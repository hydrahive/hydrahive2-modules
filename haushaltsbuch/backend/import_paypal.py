"""PayPal-Aktivitäten-CSV-Import (Phase 2).

Erwartet den offiziellen PayPal-Aktivitäten-Export (Download "Alle
Transaktionen" / "All transactions" als CSV), deutsche oder englische
Spaltennamen, Komma- oder Punkt-Dezimaltrennzeichen, Encoding
utf-8-sig oder cp1252.

Zeilen-Semantik laut Vertrag:
- Brutto ist die Hauptzeile (bank_reference = Transaktionscode -> "strong").
- Eine von Null verschiedene Gebühr (Entgelt/Fee) wird als eigene Zeile
  gemeldet (purpose "PayPal-Gebühr <Typ>", bank_reference
  "<Transaktionscode>:fee").
- Währungsumrechnungszeilen ("Allgemeine Währungsumrechnung" /
  "General Currency Conversion") werden verworfen; sie zählen stattdessen
  als Warnung an der zuletzt erzeugten Zeile (die zugehörige
  Fremdwährungs-Transaktion steht in der offiziellen Exportreihenfolge
  unmittelbar davor).
- Nur der Status "Abgeschlossen"/"Completed" wird gebucht; andere Status
  ergeben eine Fehlerzeile mit errors=("paypal_status_not_completed",).
- Fremdwährungszeilen behalten ihre Originalwährung; die bestehende
  Kontowährungs-Prüfung des Prüfbereichs (account_currency_mismatch) greift
  unverändert.
- Geld ausschließlich über Decimal-Parsing in Integer-Minor-Units, keine
  Floats.
"""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .import_parsers import ImportParseError, MAX_RECORDS, NormalizedRecord, normalize_bank_reference

# Spaltennamen: deutsche und englische Variante des offiziellen Exports.
_COLUMNS: dict[str, tuple[str, ...]] = {
    "date": ("Datum", "Date"),
    "name": ("Name",),
    "type": ("Typ", "Type"),
    "status": ("Status",),
    "currency": ("Währung", "Currency"),
    "gross": ("Brutto", "Gross"),
    "fee": ("Entgelt", "Fee"),
    "transaction_id": ("Transaktionscode", "Transaction ID"),
}
_REQUIRED_COLUMNS = ("date", "type", "status", "currency", "gross", "transaction_id")

_CURRENCY_CONVERSION_TYPES = {
    "allgemeine währungsumrechnung",
    "general currency conversion",
}
_COMPLETED_STATUSES = {"abgeschlossen", "completed"}

_DATE_FORMATS = ("%d.%m.%Y", "%m/%d/%Y", "%Y-%m-%d")


def _parse_date(value: str):
    value = value.strip()
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    raise ImportParseError("invalid_date")


def _parse_decimal_minor(raw: str) -> int:
    """Decimal-Parsing ohne Floats; erkennt Komma- und Punkt-Dezimaltrennung.

    PayPal liefert je nach Kontosprache "1.234,56" (deutsch) oder
    "1,234.56" (englisch). Enthält der Wert beide Zeichen, entscheidet das
    letzte Vorkommen über das Dezimaltrennzeichen; enthält er nur Komma,
    gilt Komma als Dezimaltrennzeichen, wenn genau zwei Nachkommastellen
    folgen (sonst Tausendertrennzeichen).
    """
    value = raw.strip()
    if not value:
        raise ImportParseError("invalid_amount")
    negative = False
    if value.startswith("-"):
        negative = True
        value = value[1:]
    elif value.startswith("(") and value.endswith(")"):
        negative = True
        value = value[1:-1]
    has_comma = "," in value
    has_dot = "." in value
    if has_comma and has_dot:
        if value.rindex(",") > value.rindex("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif has_comma:
        tail = value.split(",")[-1]
        value = value.replace(".", "").replace(",", ".") if len(tail) == 2 else value.replace(",", "")
    try:
        amount = Decimal(value)
        quantized = amount.quantize(Decimal("0.01"))
        if amount != quantized:
            raise ValueError
    except (InvalidOperation, ValueError) as exc:
        raise ImportParseError("invalid_amount") from exc
    minor = int(quantized * 100)
    return -minor if negative else minor


def _resolve_columns(fieldnames: list[str]) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    for key, candidates in _COLUMNS.items():
        resolved[key] = next((candidate for candidate in candidates if candidate in fieldnames), None)
    return resolved


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportParseError("invalid_encoding")


def _sniff_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        return ","


def parse_paypal(data: bytes) -> list[NormalizedRecord]:
    text = _decode(data)
    reader = csv.DictReader(io.StringIO(text), delimiter=_sniff_delimiter(text[:4096]))
    fieldnames = reader.fieldnames or []
    columns = _resolve_columns(fieldnames)
    if any(columns[key] is None for key in _REQUIRED_COLUMNS):
        raise ImportParseError("paypal_header_invalid")

    records: list[NormalizedRecord] = []
    for csv_line, row in enumerate(reader, 2):
        if len(records) > MAX_RECORDS:
            raise ImportParseError("too_many_records")
        if not any((value or "").strip() for value in row.values()):
            continue
        # source_line ist ein fortlaufender Zähler, nicht die echte CSV-Zeile:
        # Haupt- und Gebührenzeile teilen sich dieselbe CSV-Zeile, aber
        # module_haushaltsbuch_import_rows verlangt UNIQUE(batch_id, source_line)
        # (gleiches Muster wie import_mt940.parse_mt940).
        source_line = len(records) + 1
        row_type = (row.get(columns["type"]) or "").strip()
        if row_type.casefold() in _CURRENCY_CONVERSION_TYPES:
            if records:
                records[-1] = replace(
                    records[-1],
                    warnings=(*records[-1].warnings, "paypal_currency_conversion_discarded"),
                )
            continue

        status_value = (row.get(columns["status"]) or "").strip()
        transaction_id = normalize_bank_reference(row.get(columns["transaction_id"]))
        currency = (row.get(columns["currency"]) or "").strip().upper()
        name = (row.get(columns["name"]) or "").strip() or None if columns["name"] else None

        if status_value.casefold() not in _COMPLETED_STATUSES:
            records.append(
                NormalizedRecord(
                    source_line=source_line,
                    booking_date=None,
                    value_date=None,
                    amount_minor=None,
                    currency=None,
                    errors=("paypal_status_not_completed",),
                )
            )
            continue

        try:
            booking_date = _parse_date(row.get(columns["date"]) or "")
            gross_minor = _parse_decimal_minor(row.get(columns["gross"]) or "")
            fee_raw = row.get(columns["fee"]) if columns["fee"] else None
            fee_minor = _parse_decimal_minor(fee_raw) if fee_raw and fee_raw.strip() else 0
        except ImportParseError as exc:
            records.append(
                NormalizedRecord(
                    source_line=source_line,
                    booking_date=None,
                    value_date=None,
                    amount_minor=None,
                    currency=None,
                    errors=(str(exc),),
                )
            )
            continue

        if len(currency) != 3 or not currency.isalpha():
            records.append(
                NormalizedRecord(
                    source_line=source_line,
                    booking_date=None,
                    value_date=None,
                    amount_minor=None,
                    currency=None,
                    errors=("invalid_currency",),
                )
            )
            continue

        records.append(
            NormalizedRecord(
                source_line=source_line,
                booking_date=booking_date,
                value_date=booking_date,
                amount_minor=gross_minor,
                currency=currency,
                counterparty=name,
                purpose=row_type or None,
                bank_reference=transaction_id,
            )
        )
        if fee_minor != 0:
            fee_reference = f"{transaction_id}:fee" if transaction_id else None
            records.append(
                NormalizedRecord(
                    source_line=len(records) + 1,
                    booking_date=booking_date,
                    value_date=booking_date,
                    amount_minor=fee_minor,
                    currency=currency,
                    counterparty=name,
                    purpose=f"PayPal-Gebühr {row_type}".strip(),
                    bank_reference=fee_reference,
                )
            )
    return records
