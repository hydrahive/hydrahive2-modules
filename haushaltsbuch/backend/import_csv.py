from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .import_parsers import (
    CsvMapping,
    ImportParseError,
    MAX_RECORDS,
    NormalizedRecord,
    mask_bank_identifier,
    normalize_bank_reference,
)


def _value(row: dict[str, str | None], column: str | None) -> str | None:
    if not column:
        return None
    if column not in row:
        raise ImportParseError("csv_column_missing")
    value = (row[column] or "").strip()
    return value or None


def _parse_date(value: str, configured_format: str) -> date:
    formats = dict.fromkeys((configured_format, "%d.%m.%Y", "%d.%m.%y"))
    for date_format in formats:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    raise ImportParseError("invalid_date")


def _amount_minor(value: str, decimal_separator: str) -> int:
    normalized = value.replace(" ", "")
    if decimal_separator == ",":
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", "")
    try:
        amount = Decimal(normalized)
        quantized = amount.quantize(Decimal("0.01"))
        if amount != quantized:
            raise ValueError
        return int(quantized * 100)
    except (InvalidOperation, ValueError) as exc:
        raise ImportParseError("invalid_amount") from exc


def _parse_row(
    row: dict[str, str | None], source_line: int, mapping: CsvMapping
) -> NormalizedRecord:
    raw_date = _value(row, mapping.booking_date)
    booking_date = _parse_date(raw_date or "", mapping.date_format)
    raw_value_date = _value(row, mapping.value_date)
    value_date = _parse_date(raw_value_date, mapping.date_format) if raw_value_date else None
    if mapping.amount:
        amount = _amount_minor(_value(row, mapping.amount) or "", mapping.decimal_separator)
    else:
        debit = _value(row, mapping.debit_amount)
        credit = _value(row, mapping.credit_amount)
        if bool(debit) == bool(credit):
            raise ImportParseError("debit_credit_invalid")
        amount = (
            -abs(_amount_minor(debit, mapping.decimal_separator))
            if debit
            else abs(_amount_minor(credit or "", mapping.decimal_separator))
        )
    currency = (_value(row, mapping.currency) or mapping.default_currency).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ImportParseError("invalid_currency")
    return NormalizedRecord(
        source_line=source_line,
        booking_date=booking_date,
        value_date=value_date,
        amount_minor=amount,
        currency=currency,
        counterparty=_value(row, mapping.counterparty),
        purpose=_value(row, mapping.purpose),
        counterparty_identifier=mask_bank_identifier(
            _value(row, mapping.counterparty_identifier)
        ),
        bank_reference=normalize_bank_reference(_value(row, mapping.bank_reference)),
        category_hint=_value(row, mapping.category_hint),
    )


def parse_csv(data: bytes, mapping: CsvMapping) -> list[NormalizedRecord]:
    try:
        text = data.decode(mapping.encoding)
    except (UnicodeDecodeError, LookupError) as exc:
        raise ImportParseError("invalid_encoding") from exc
    reader = csv.DictReader(io.StringIO(text), delimiter=mapping.delimiter)
    if not reader.fieldnames:
        raise ImportParseError("csv_header_missing")
    records: list[NormalizedRecord] = []
    for source_line, row in enumerate(reader, 2):
        if source_line - 1 > MAX_RECORDS:
            raise ImportParseError("too_many_records")
        if not any(value and value.strip() for value in row.values()):
            continue
        try:
            records.append(_parse_row(row, source_line, mapping))
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
    return records
