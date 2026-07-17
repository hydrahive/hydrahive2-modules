from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .import_parsers import (
    ImportParseError,
    MAX_RECORDS,
    NormalizedRecord,
    mask_bank_identifier,
    normalize_bank_reference,
)

_TRANSACTION = re.compile(
    r"^(?P<date>\d{6})(?P<entry>\d{4})?(?P<sign>R?[DC])"
    r"(?P<funds>[A-Z])?(?P<amount>\d+(?:,\d*)?).*?"
    r"(?://(?P<reference>[^\r\n]+))?$"
)


def _tag_lines(text: str) -> list[tuple[str, str]]:
    tags: list[tuple[str, str]] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = re.match(r"^:([^:]+):(.*)$", line)
        if match:
            tags.append((match.group(1), match.group(2)))
        elif tags and line:
            key, value = tags[-1]
            tags[-1] = (key, f"{value}\n{line}")
    return tags


def _structured(value: str, key: str) -> str | None:
    match = re.search(rf"(?:^|\s){key}\+(.+?)(?=\s[A-Z]{{2,5}}\+|$)", value, re.DOTALL)
    return " ".join(match.group(1).split()) if match else None


def _dates(value_raw: str, entry_raw: str | None) -> tuple[date, date]:
    value_date = date(
        2000 + int(value_raw[:2]), int(value_raw[2:4]), int(value_raw[4:6])
    )
    if not entry_raw:
        return value_date, value_date
    booking_date = date(value_date.year, int(entry_raw[:2]), int(entry_raw[2:4]))
    distance = (booking_date - value_date).days
    if distance > 180:
        booking_date = booking_date.replace(year=booking_date.year - 1)
    elif distance < -180:
        booking_date = booking_date.replace(year=booking_date.year + 1)
    return booking_date, value_date


def _parse_transaction(
    value: str,
    detail: str,
    currency: str,
    source_line: int,
) -> NormalizedRecord:
    match = _TRANSACTION.match(value)
    if not match:
        raise ImportParseError("invalid_mt940_record")
    try:
        booking_date, value_date = _dates(match.group("date"), match.group("entry"))
        parsed_amount = Decimal(match.group("amount").replace(",", "."))
        quantized = parsed_amount.quantize(Decimal("0.01"))
        if parsed_amount != quantized:
            raise ValueError
        amount = int(quantized * 100)
    except (ValueError, InvalidOperation) as exc:
        raise ImportParseError("invalid_mt940_record") from exc
    if match.group("sign") in {"D", "RC"}:
        amount = -abs(amount)
    else:
        amount = abs(amount)
    reference = normalize_bank_reference(
        _structured(detail, "EREF") or (match.group("reference") or "").strip() or None
    )
    return NormalizedRecord(
        source_line=source_line,
        booking_date=booking_date,
        value_date=value_date,
        amount_minor=amount,
        currency=currency,
        counterparty=_structured(detail, "NAME"),
        purpose=_structured(detail, "SVWZ") or (" ".join(detail.split()) or None),
        counterparty_identifier=mask_bank_identifier(_structured(detail, "IBAN")),
        bank_reference=reference,
    )


def parse_mt940(data: bytes) -> list[NormalizedRecord]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252")
    tags = _tag_lines(text)
    currency = "EUR"
    records: list[NormalizedRecord] = []
    for index, (tag, value) in enumerate(tags):
        if tag in {"60F", "60M"} and len(value) >= 10:
            currency = value[7:10].upper()
        if tag != "61":
            continue
        if len(records) >= MAX_RECORDS:
            raise ImportParseError("too_many_records")
        source_line = len(records) + 1
        detail = tags[index + 1][1] if index + 1 < len(tags) and tags[index + 1][0] == "86" else ""
        try:
            records.append(_parse_transaction(value, detail, currency, source_line))
        except ImportParseError as exc:
            records.append(
                NormalizedRecord(
                    source_line=source_line,
                    booking_date=None,
                    value_date=None,
                    amount_minor=None,
                    currency=currency,
                    errors=(str(exc),),
                )
            )
    return records
