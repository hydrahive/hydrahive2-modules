from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_RECORDS = 10_000
ImportFormat = Literal["camt", "mt940", "csv"]


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
    encoding: Literal["utf-8", "utf-8-sig", "cp1252", "iso-8859-1"] = "utf-8"
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


def detect_format(data: bytes, filename: str = "") -> ImportFormat:
    _check_size(data)
    sample = data[:4096].lstrip()
    lower_name = filename.lower()
    if sample.startswith(b"<"):
        return "camt"
    text = sample.decode("latin-1", errors="ignore")
    if re.search(r"(?m)^:(?:20|25|28C|60[FM]|61):", text):
        return "mt940"
    if lower_name.endswith(".csv") or any(char in text for char in (";", ",", "\t")):
        return "csv"
    raise ImportParseError("unsupported_format")


def parse_import(
    data: bytes,
    import_format: str = "auto",
    csv_mapping: CsvMapping | None = None,
    *,
    filename: str = "",
) -> list[NormalizedRecord]:
    _check_size(data)
    selected = detect_format(data, filename) if import_format == "auto" else import_format.lower()
    if selected == "camt":
        from .import_camt import parse_camt

        records = parse_camt(data)
    elif selected == "mt940":
        from .import_mt940 import parse_mt940

        records = parse_mt940(data)
    elif selected == "csv":
        if csv_mapping is None:
            raise ImportParseError("csv_mapping_required")
        from .import_csv import parse_csv

        records = parse_csv(data, csv_mapping)
    else:
        raise ImportParseError("unsupported_format")
    if len(records) > MAX_RECORDS:
        raise ImportParseError("too_many_records")
    if not records:
        raise ImportParseError("no_records")
    return records


def _check_size(data: bytes) -> None:
    if len(data) > MAX_FILE_SIZE:
        raise ImportParseError("file_too_large")
