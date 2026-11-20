"""Erkennung + Umschreibung von Bank-CSVs anhand der BankTemplate-Vorlagen aus
import_bank_csv.py (Dateigrößenlimit, siehe Hinweis dort).

Ablauf: Zeichensatz erkennen (import_csv.detect_encoding) -> Kopfzeile in den
ersten _MAX_HEADER_SEARCH_LINES Zeilen suchen (normalisierter Vergleich) ->
Daten ab Kopfzeile ausschneiden, auf normalisierte Spaltennamen umgeschrieben
+ ggf. bank-spezifische Nachbearbeitung (DKB-Gegenpartei je Richtung,
Commerzbank Betrag=0 raus, Fußzeilen ohne gültiges Buchungsdatum raus) ->
CsvMapping -> vorhandener parse_csv()-Weg.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import replace

from .import_bank_csv import TEMPLATES, BankTemplate, normalize_header_name
from .import_csv import detect_encoding, parse_csv
from .import_parsers import CsvMapping, ImportParseError, NormalizedRecord

_DATE_LINE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{2,4}$")
_MAX_HEADER_SEARCH_LINES = 20


def find_header_line(text: str, delimiter: str, header: tuple[str, ...]) -> int | None:
    lines = text.splitlines()
    for idx, line in enumerate(lines[:_MAX_HEADER_SEARCH_LINES]):
        try:
            cols = next(csv.reader([line], delimiter=delimiter))
        except (csv.Error, StopIteration):
            continue
        if tuple(normalize_header_name(c) for c in cols) == header:
            return idx
    return None


def detect_bank_template(data: bytes) -> tuple[BankTemplate, str, int] | None:
    """(template, encoding, header_line_idx) oder None, wenn kein bekannter
    Kopf passt (Aufrufer fällt dann auf csv_mapping_required zurück)."""
    try:
        encoding = detect_encoding(data)
    except ImportParseError:
        return None
    text = data.decode(encoding)
    for template in TEMPLATES:
        idx = find_header_line(text, ";", template.header)
        if idx is not None:
            return template, encoding, idx
    return None


def _dkb_counterparty(row: list[str], index: dict[str, int]) -> str:
    """DKB: Eingang -> Zahlungspflichtige*r zeigt den Absender, Ausgang ->
    Zahlungsempfänger*in zeigt den Empfänger. Je Richtung ist genau eines der
    beiden Felder die tatsächliche Gegenpartei; das andere steht laut
    Beispieldatei auf dem eigenen Namen bzw. ist identisch - zusammenführen
    statt zwei irrelevante Spalten parallel vorzuhalten."""
    richtung = row[index["umsatztyp"]].strip().casefold()
    pflichtiger = row[index["zahlungspflichtige*r"]]
    empfaenger = row[index["zahlungsempfaenger*in"]]
    return pflichtiger if richtung == "eingang" else empfaenger


def _rewrite(text: str, header_idx: int, template: BankTemplate) -> tuple[str, list[dict[str, str]]]:
    """Schneidet ab der Kopfzeile zu, normalisiert die Spaltennamen, wendet
    Sonderregeln an (DKB-Gegenpartei, Commerzbank Betrag=0, Fußzeilen ohne
    gültiges Buchungsdatum) und gibt (neue CSV als Text, behaltene Rohzeilen
    je normalisierter Spalte) zurück - Letzteres für die pending-Markierung
    nach dem eigentlichen Parse."""
    lines = text.splitlines()[header_idx:]
    rows_iter = csv.reader(lines, delimiter=";")
    original_header = next(rows_iter)
    normalized_header = [normalize_header_name(c) for c in original_header]
    index = {name: position for position, name in enumerate(normalized_header)}
    out_fieldnames = [*normalized_header, "_gegenpartei"] if template.dkb_counterparty else normalized_header
    out_rows: list[list[str]] = []
    kept_raw_rows: list[dict[str, str]] = []
    booking_idx = index.get(template.mapping["booking_date"])
    for raw in rows_iter:
        if len(raw) < len(normalized_header):
            continue
        if booking_idx is not None and not _DATE_LINE.match(raw[booking_idx].strip()):
            continue  # Fußzeile/Saldo-Zeile (z.B. "Kontostand;..."), keine Buchung
        if template.skip_zero_amount and _is_zero_amount(raw, index):
            continue
        out_row = list(raw[: len(normalized_header)])
        if template.dkb_counterparty:
            out_row.append(_dkb_counterparty(raw, index))
        out_rows.append(out_row)
        kept_raw_rows.append(dict(zip(normalized_header, raw)))
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(out_fieldnames)
    writer.writerows(out_rows)
    return buffer.getvalue(), kept_raw_rows


def _is_zero_amount(row: list[str], index: dict[str, int]) -> bool:
    raw = row[index["betrag"]].strip().replace(" ", "").replace(",", ".")
    try:
        return float(raw) == 0.0
    except ValueError:
        return False


def _mark_pending(
    records: list[NormalizedRecord], kept_raw_rows: list[dict[str, str]], template: BankTemplate
) -> list[NormalizedRecord]:
    if not template.pending_column:
        return records
    marked = []
    for record, raw in zip(records, kept_raw_rows):
        value = (raw.get(template.pending_column) or "").strip().casefold()
        if value in template.pending_values:
            marked.append(replace(record, errors=(*record.errors, "pending_transaction")))
        else:
            marked.append(record)
    return marked


def parse_bank_csv(data: bytes) -> tuple[list[NormalizedRecord], BankTemplate, str] | None:
    """Erkennt eine Bank-Vorlage und liefert (Records, Template, Encoding),
    oder None wenn kein bekannter Kopf passt (Aufrufer fällt dann auf den
    bisherigen Weg - csv_mapping_required - zurück)."""
    detected = detect_bank_template(data)
    if detected is None:
        return None
    template, encoding, header_idx = detected
    text = data.decode(encoding)
    rewritten_text, kept_raw_rows = _rewrite(text, header_idx, template)
    mapping_kwargs = {key: value for key, value in template.mapping.items() if key != "currency" or True}
    mapping = CsvMapping(encoding="utf-8", **mapping_kwargs)
    records = parse_csv(rewritten_text.encode("utf-8"), mapping)
    records = _mark_pending(records, kept_raw_rows, template)
    return records, template, encoding
