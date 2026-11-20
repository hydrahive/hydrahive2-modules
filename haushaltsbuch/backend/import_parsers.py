from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_RECORDS = 10_000
ImportFormat = Literal["camt", "mt940", "csv", "pdf", "paypal"]


class ImportParseError(ValueError):
    """A safe, client-facing import validation error."""


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    source_line: int
    booking_date: date | None
    value_date: date | None
    amount_minor: int | None
    currency: str | None
    counterparty: str | None = None
    purpose: str | None = None
    counterparty_identifier: str | None = None
    bank_reference: str | None = None
    category_hint: str | None = None
    counter_account_id: int | None = None
    category_id: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CsvMapping:
    booking_date: str
    amount: str | None = None
    debit_amount: str | None = None
    credit_amount: str | None = None
    value_date: str | None = None
    currency: str | None = None
    counterparty: str | None = None
    purpose: str | None = None
    bank_reference: str | None = None
    counterparty_identifier: str | None = None
    category_hint: str | None = None
    delimiter: Literal[";", ",", "\t"] = ";"
    encoding: Literal["utf-8", "utf-8-sig", "cp1252", "iso-8859-1", "auto"] = "auto"
    decimal_separator: Literal[".", ","] = ","
    date_format: str = "%d.%m.%Y"
    default_currency: str = "EUR"

    def __post_init__(self) -> None:
        if not self.amount and not (self.debit_amount and self.credit_amount):
            raise ValueError("amount or debit/credit mapping required")


def mask_bank_identifier(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"\s+", "", value)
    return f"****{compact[-4:]}" if compact else None


_EMPTY_REFERENCES = {"NONREF", "NOTPROVIDED", "NOTAVAILABLE", "UNKNOWN", "N/A"}


def normalize_bank_reference(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split())
    sentinel = re.sub(r"[\s_-]+", "", normalized).upper()
    return None if sentinel in _EMPTY_REFERENCES else normalized


_PAYPAL_HEADER_HINTS = (
    ("transaktionscode", "brutto"),
    ("transaction id", "gross"),
)


def _looks_like_paypal_header(text: str) -> bool:
    lower = text.casefold()
    first_line = lower.splitlines()[0] if lower.splitlines() else lower
    return any(
        reference in first_line and gross in first_line
        for reference, gross in _PAYPAL_HEADER_HINTS
    )


def detect_format(data: bytes, filename: str = "") -> ImportFormat:
    check_file_size(data)
    sample = data[:4096].lstrip()
    lower_name = filename.lower()
    if sample.startswith(b"%PDF-"):
        return "pdf"
    if sample.startswith(b"<"):
        return "camt"
    text = sample.decode("latin-1", errors="ignore")
    if re.search(r"(?m)^:(?:20|25|28C|60[FM]|61):", text):
        return "mt940"
    if lower_name.endswith(".csv") or any(char in text for char in (";", ",", "\t")):
        if _looks_like_paypal_header(text):
            return "paypal"
        return "csv"
    raise ImportParseError("unsupported_format")


def parse_import(
    data: bytes,
    import_format: str = "auto",
    csv_mapping: CsvMapping | None = None,
    *,
    filename: str = "",
    detected: dict | None = None,
) -> list[NormalizedRecord]:
    """`detected` (optional, wird befüllt): {"bank": {"id","label"}|None,
    "encoding": str|None} - für die Batch-Antwort (detected_bank/
    detected_encoding, Vertrag hb-bank-csv-notes.md). Nur beim CSV-Pfad
    gesetzt, sonst unverändert (leer) gelassen."""
    check_file_size(data)
    selected = detect_format(data, filename) if import_format == "auto" else import_format.lower()
    if selected == "camt":
        from .import_camt import parse_camt

        records = parse_camt(data)
    elif selected == "mt940":
        from .import_mt940 import parse_mt940

        records = parse_mt940(data)
    elif selected == "csv":
        from .import_csv import detect_encoding, parse_csv

        if csv_mapping is None:
            from .import_bank_csv_rewrite import parse_bank_csv

            bank_result = parse_bank_csv(data)
            if bank_result is None:
                raise ImportParseError("csv_mapping_required")
            records, template, encoding = bank_result
            if detected is not None:
                detected["bank"] = {"id": template.id, "label": template.label}
                detected["encoding"] = encoding
        else:
            records = parse_csv(data, csv_mapping)
            if detected is not None:
                detected["bank"] = None
                try:
                    detected["encoding"] = (
                        detect_encoding(data) if csv_mapping.encoding in ("auto", "", None) else csv_mapping.encoding
                    )
                except ImportParseError:
                    detected["encoding"] = None
    elif selected == "pdf":
        from .import_pdf import parse_pdf

        records = parse_pdf(data)
    elif selected == "paypal":
        from .import_paypal import parse_paypal

        records = parse_paypal(data)
    else:
        raise ImportParseError("unsupported_format")
    if len(records) > MAX_RECORDS:
        raise ImportParseError("too_many_records")
    if not records:
        raise ImportParseError("no_records")
    return records


def check_file_size(data: bytes) -> None:
    if len(data) > MAX_FILE_SIZE:
        raise ImportParseError("file_too_large")
