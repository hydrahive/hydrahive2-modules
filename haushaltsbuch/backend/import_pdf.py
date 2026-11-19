"""PDF-Kontoauszug-Import (Phase 2).

Textextraktion ausschließlich über die Kern-Sandbox
`hydrahive.tools._document_process.run` (bwrap+prlimit auf Linux,
fail-closed): kein ungesicherter Python-PDF-Parser, kein zusätzliches
Paket im venv (pypdf/pdfminer fehlen bewusst und bleiben es). Ist die
Sandbox nicht verfügbar (kein bwrap/prlimit/pdftotext), wird NICHT auf
einen ungesicherten Weg zurückgefallen, sondern pdf_extraction_unavailable
gemeldet.

Zeilenparser: konservativ für gängige deutsche Kontoauszüge. Erkanntes
Muster pro Buchungszeile: Buchungsdatum [Valutadatum] Text Betrag, wobei
der Betrag entweder ein Vorzeichen (+/-) oder ein Soll/Haben-Kürzel (S/H)
trägt. Folgezeilen ohne eigenes Datum/Betrag werden als zusätzlicher
Verwendungszweck an die letzte Buchungszeile angehängt. Unklare Zeilen
(Betrag oder Datum nicht eindeutig, z.B. ganz ohne Vorzeichen) werden
nicht geraten, sondern als eigene Zeile mit errors=("pdf_line_ambiguous",)
gemeldet.

Keine Roh-Bankdaten (Kontonummern, volle Buchungstexte) werden geloggt.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from hydrahive.tools import _document_process

from .import_parsers import ImportParseError, NormalizedRecord

MAX_PAGES = 50
_INFO_TIMEOUT = 15
_TEXT_TIMEOUT = 45
_MIN_ALNUM_CHARS = 20

# Auszugs-Zeitraum im Kopf, z.B. "01.03.2026 - 31.03.2026" oder "... bis ...".
_PERIOD_RANGE = re.compile(
    r"(\d{2})\.(\d{2})\.(\d{4})\s*(?:-|bis)\s*(\d{2})\.(\d{2})\.(\d{4})"
)

# Datum/Daten am Zeilenanfang: "01.03." oder "01.03.2026", optional ein zweites (Valuta-)Datum.
_LEADING_DATES = re.compile(
    r"^\s*(\d{2}\.\d{2}\.(?:\d{2,4})?)\s+(?:(\d{2}\.\d{2}\.(?:\d{2,4})?)\s+)?(.*)$"
)

# Betrag am Zeilenende: optionales Vorzeichen vor oder S/H-Kürzel nach dem Betrag,
# z.B. "-850,00", "850,00+", "850,00 H".
_TRAILING_AMOUNT = re.compile(
    r"^(?P<text>.*?)\s+"
    r"(?P<sign_pre>[+-])?"
    r"(?P<amount>\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})"
    r"\s*(?P<sign_post>[+-]|[SH])?\s*$"
)

_CONTINUATION_PREFIX = re.compile(r"^\s*(Verwendungszweck:?|SVWZ\+?)\s*", re.IGNORECASE)


class PdfImportError(ImportParseError):
    """Alias, damit die Fehlercodes dieses Moduls klar erkennbar sind."""


def _private_work_dir() -> Path:
    base = Path(tempfile.mkdtemp(prefix="hh-pdf-import-"))
    base.chmod(0o700)
    return base


def _run_sandboxed(
    argv: list[str], timeout: float, root: Path, work: Path, max_bytes: int
) -> str:
    try:
        return _document_process.run(argv, timeout, root, work, max_bytes)
    except _document_process.DocumentIsolationError as exc:
        raise PdfImportError("pdf_extraction_unavailable") from exc


def _page_count(path: Path, work: Path) -> int:
    try:
        output = _run_sandboxed(
            ["pdfinfo", str(path)], _INFO_TIMEOUT, path.parent, work, 262_144
        )
    except _document_process.ProcessFailed as exc:
        raise PdfImportError("pdf_unreadable") from exc
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if not match or int(match.group(1)) < 1:
        raise PdfImportError("pdf_unreadable")
    return int(match.group(1))


def _extract_text(path: Path, pages: int, work: Path) -> str:
    argv = ["pdftotext", "-f", "1", "-l", str(pages), "-layout", str(path), "-"]
    try:
        return _run_sandboxed(argv, _TEXT_TIMEOUT, path.parent, work, 4_000_000)
    except _document_process.ProcessFailed as exc:
        raise PdfImportError("pdf_unreadable") from exc


def _has_text_layer(text: str) -> bool:
    return sum(character.isalnum() for character in text) >= _MIN_ALNUM_CHARS


def _statement_year_hint(text: str) -> int | None:
    """Jahr aus dem im Auszug genannten Zeitraum, für Zeilen mit nur TT.MM."""
    match = _PERIOD_RANGE.search(text)
    if not match:
        return None
    return int(match.group(6))


def _parse_date_token(token: str, year_hint: int | None) -> date | None:
    parts = token.rstrip(".").split(".")
    if len(parts) == 2:
        day, month = parts
        if year_hint is None:
            return None
        try:
            return date(year_hint, int(month), int(day))
        except ValueError:
            return None
    if len(parts) == 3:
        day, month, year = parts
        if len(year) == 2:
            year = f"20{year}"
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            return None
    return None


def _parse_amount(raw: str, sign_pre: str | None, sign_post: str | None) -> int | None:
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None
    quantized = value.quantize(Decimal("0.01"))
    if value != quantized:
        return None
    minor = int(quantized * 100)
    negative = sign_pre == "-" or sign_post in ("-", "S")
    positive = sign_pre == "+" or sign_post in ("+", "H")
    if negative and positive:
        return None
    if negative:
        return -abs(minor)
    if positive:
        return abs(minor)
    # Kein eindeutiges Vorzeichen (weder +/- noch S/H): nicht raten, sondern
    # als unklar behandeln (Aufrufer markiert die Zeile als pdf_line_ambiguous).
    return None


def _parse_line(line: str, source_line: int, year_hint: int | None) -> NormalizedRecord | None:
    """Parst eine Zeile als Buchung. None, wenn die Zeile kein Datum am Anfang
    trägt (Kopf-/Fußzeilen, Verwendungszweck-Folgezeilen)."""
    date_match = _LEADING_DATES.match(line)
    if not date_match:
        return None
    booking_token, value_token, rest = date_match.groups()
    booking_date = _parse_date_token(booking_token, year_hint)
    value_date = _parse_date_token(value_token, year_hint) if value_token else booking_date
    amount_match = _TRAILING_AMOUNT.match(rest)
    if booking_date is None or amount_match is None:
        return NormalizedRecord(
            source_line=source_line,
            booking_date=None,
            value_date=None,
            amount_minor=None,
            currency=None,
            errors=("pdf_line_ambiguous",),
        )
    amount_minor = _parse_amount(
        amount_match.group("amount"),
        amount_match.group("sign_pre"),
        amount_match.group("sign_post"),
    )
    if amount_minor is None:
        return NormalizedRecord(
            source_line=source_line,
            booking_date=None,
            value_date=None,
            amount_minor=None,
            currency=None,
            errors=("pdf_line_ambiguous",),
        )
    purpose = amount_match.group("text").strip() or None
    return NormalizedRecord(
        source_line=source_line,
        booking_date=booking_date,
        value_date=value_date,
        amount_minor=amount_minor,
        currency="EUR",
        purpose=purpose,
        bank_reference=None,
    )


def _append_continuation(record: NormalizedRecord, line: str) -> NormalizedRecord:
    text = _CONTINUATION_PREFIX.sub("", line).strip()
    if not text:
        return record
    purpose = f"{record.purpose} {text}".strip() if record.purpose else text
    return replace(record, purpose=purpose[:500])


def _parse_text(text: str) -> list[NormalizedRecord]:
    year_hint = _statement_year_hint(text)
    records: list[NormalizedRecord] = []
    for source_line, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        parsed = _parse_line(line, source_line, year_hint)
        if parsed is not None:
            records.append(parsed)
            continue
        if records and not records[-1].errors:
            records[-1] = _append_continuation(records[-1], line)
    return records


def parse_pdf(data: bytes) -> list[NormalizedRecord]:
    """Extrahiert Buchungszeilen aus einem Bank-PDF-Kontoauszug mit Textschicht.

    Bytes werden in ein privates (0700) tempfile-Verzeichnis geschrieben,
    dort ausschließlich sandboxed per pdfinfo/pdftotext gelesen, und danach
    vollständig gelöscht - unabhängig vom Ausgang.
    """
    work_root = _private_work_dir()
    try:
        pdf_path = work_root / "input.pdf"
        pdf_path.write_bytes(data)
        pdf_path.chmod(0o600)
        work = work_root / "work"
        work.mkdir(mode=0o700, exist_ok=True)
        pages = _page_count(pdf_path, work)
        if pages > MAX_PAGES:
            raise PdfImportError("pdf_too_many_pages")
        text = _extract_text(pdf_path, pages, work)
        if not _has_text_layer(text):
            raise PdfImportError("pdf_no_text_layer")
        records = _parse_text(text)
        if not records:
            raise PdfImportError("pdf_no_transactions")
        return records
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
