"""Defensive Konvertierung externer Lidl-Belegwerte."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

_NUMBER = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_CURRENCY_EDGE = re.compile(r"^(?:EUR|€)|(?:EUR|€)$", re.I)


def _normalized_number(text: str) -> str | None:
    sign = text[0] if text[:1] in ("+", "-") else ""
    unsigned = text[1:] if sign else text
    if "," in unsigned and "." in unsigned:
        decimal_separator = "," if unsigned.rfind(",") > unsigned.rfind(".") else "."
        grouping_separator = "." if decimal_separator == "," else ","
        if unsigned.count(decimal_separator) != 1:
            return None
        integer, fraction = unsigned.rsplit(decimal_separator, 1)
        groups = integer.split(grouping_separator)
        if not groups[0].isdigit() or not 1 <= len(groups[0]) <= 3:
            return None
        if any(len(group) != 3 or not group.isdigit() for group in groups[1:]):
            return None
        unsigned = "".join(groups) + "." + fraction
    elif unsigned.count(",") == 1:
        unsigned = unsigned.replace(",", ".")
    elif unsigned.count(",") > 1 or unsigned.count(".") > 1:
        return None
    normalized = sign + unsigned
    return normalized if _NUMBER.fullmatch(normalized) else None


def decimal_value(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, dict):
        for key in (
            "amount", "value", "totalAmount", "discountAmount", "savings", "couponTitle",
        ):
            if key in value and (parsed := decimal_value(value[key])) is not None:
                return parsed
        return None
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    text = _CURRENCY_EDGE.sub("", text)
    if not text or len(text) > 64:
        return None
    normalized = _normalized_number(text)
    if normalized is None:
        return None
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or parsed.adjusted() > 16:
        return None
    return parsed if parsed.as_tuple().exponent >= -6 else None


def minor_value(value) -> int | None:
    parsed = decimal_value(value)
    if parsed is None or parsed.normalize().as_tuple().exponent < -2:
        return None
    try:
        minor = int((parsed * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (DecimalException, ValueError, OverflowError):
        return None
    return minor if -(2**63 - 1) <= minor <= 2**63 - 1 else None


def currency_code(value) -> str | None:
    if isinstance(value, dict):
        for key in ("code", "currency", "currencyCode", "isoCode"):
            if key in value and (parsed := currency_code(value[key])) is not None:
                return parsed
        return None
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    return code if code == "EUR" else None


def bounded_text(
    value, limit: int, warnings: list[str], warning: str,
) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > limit:
        warnings.append(warning)
        return text[:limit]
    return text


def iso_datetime(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def localize_german_time(value: datetime) -> tuple[datetime, str | None]:
    if value.tzinfo is not None:
        return value, None
    zone = ZoneInfo("Europe/Berlin")
    first = value.replace(tzinfo=zone, fold=0)
    second = value.replace(tzinfo=zone, fold=1)
    first_valid = first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == value
    second_valid = second.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == value
    if not first_valid and not second_valid:
        return value, "timezone_nonexistent"
    if first_valid and second_valid and first.utcoffset() != second.utcoffset():
        return value, "timezone_ambiguous"
    return (first if first_valid else second), "timezone_inferred_de"


def valid_gtin(value) -> str | None:
    digits = str(value or "").strip()
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return None
    expected = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(digits[:-1]))
    )
    return digits if (10 - expected % 10) % 10 == int(digits[-1]) else None
