"""Defensive Normalisierung deutscher Lidl-Belege in kanonische Dataclasses."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP

from .loyalty_provider import InvalidProviderData
from .loyalty_receipt_models import ProviderReceipt, ProviderReceiptAdjustment, ProviderReceiptItem


def _decimal(value) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        parsed = Decimal(text)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _minor(value) -> int | None:
    parsed = _decimal(value)
    if parsed is None:
        return None
    try:
        minor = int((parsed * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (DecimalException, ValueError, OverflowError):
        return None
    return minor if -(2**63) <= minor <= 2**63 - 1 else None


def _gtin(value) -> str | None:
    digits = str(value or "").strip()
    if not digits.isdigit() or len(digits) not in (8, 12, 13, 14):
        return None
    expected = sum(int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(digits[:-1])))
    return digits if (10 - expected % 10) % 10 == int(digits[-1]) else None


def _text(value, limit: int, warnings: list[str], warning: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > limit:
        warnings.append(warning)
        return text[:limit]
    return text


def _date(value) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _adjustment(raw, kind: str, sequence: int) -> ProviderReceiptAdjustment | None:
    if raw is None:
        return None
    data = raw if isinstance(raw, dict) else {"amount": raw}
    amount = _minor(data.get("amount", data.get("value", data.get("totalAmount"))))
    if amount is None:
        return None
    if kind in ("discount", "coupon"):
        amount = -abs(amount)
    description = data.get("description") or data.get("name")
    description = str(description).strip()[:1000] if description else None
    return ProviderReceiptAdjustment(kind, amount, description, sequence)


def _item(raw: dict, sequence: int, warnings: list[str]):
    name = _text(raw.get("name"), 1000, warnings, "item_name_truncated")
    if name is None:
        name = "Unbekannter Artikel"
        warnings.append("missing_item_name")
    code, gtin = raw.get("codeInput"), _gtin(raw.get("codeInput"))
    if code and gtin is None:
        warnings.append("invalid_gtin")
    quantity = _decimal(raw.get("quantity"))
    unit_price = _minor(raw.get("currentUnitPrice"))
    total = _minor(raw.get("originalAmount"))
    is_return = bool((quantity is not None and quantity < 0) or (total is not None and total < 0))
    item = ProviderReceiptItem(
        sequence=sequence, original_name=name, gtin=gtin,
        quantity=format(quantity, "f") if quantity is not None else None,
        unit="kg" if raw.get("isWeight") is True else "piece",
        unit_price_minor=unit_price, total_minor=total,
        tax_group=_text(
            raw.get("taxGroupName") or raw.get("taxGroup"), 120, warnings,
            "tax_group_truncated",
        ), is_return=is_return,
    )
    adjustments = []
    for discount in raw.get("discounts") or []:
        adjustment = _adjustment(discount, "discount", sequence)
        if adjustment:
            adjustments.append(adjustment)
        else:
            warnings.append("invalid_discount")
    deposit = _adjustment(raw.get("deposit"), "deposit", sequence)
    if deposit:
        adjustments.append(deposit)
    return item, adjustments


def normalize_receipt(payload: dict) -> ProviderReceipt:
    if not isinstance(payload, dict):
        raise InvalidProviderData("receipt_id_missing")
    provider_id = str(payload.get("id") or "").strip()
    if not provider_id or len(provider_id) > 256:
        raise InvalidProviderData("receipt_id_missing")
    warnings: list[str] = []
    total = _minor(payload.get("totalAmount"))
    currency_data = payload.get("currency")
    currency = currency_data.get("code") if isinstance(currency_data, dict) else currency_data
    currency = (
        currency.upper() if isinstance(currency, str)
        and len(currency) == 3 and currency.isalpha() else None
    )
    purchased_at = _date(payload.get("date"))
    if total is None:
        warnings.append("missing_total")
    if currency is None:
        warnings.append("missing_currency")
    if purchased_at is None:
        warnings.append("missing_date")
    elif purchased_at.tzinfo is None:
        warnings.append("timezone_unknown")
    items, adjustments = [], []
    for sequence, raw in enumerate(payload.get("itemsLine") or []):
        if not isinstance(raw, dict):
            warnings.append("invalid_item")
            continue
        item, item_adjustments = _item(raw, sequence, warnings)
        items.append(item)
        adjustments.extend(item_adjustments)
    for raw in payload.get("couponsUsed") or []:
        adjustment = _adjustment(raw, "coupon", -1)
        if adjustment:
            adjustments.append(adjustment)
        else:
            warnings.append("coupon_amount_unknown")
    store = payload.get("store") if isinstance(payload.get("store"), dict) else {}
    total_discount = _minor(payload.get("totalDiscount"))
    total_discount = abs(total_discount) if total_discount is not None else None
    store_id = _text(store.get("id"), 256, warnings, "store_id_truncated")
    store_name = _text(store.get("name"), 240, warnings, "store_name_truncated")
    store_address = _text(store.get("address"), 1000, warnings, "store_address_truncated")
    normalized = {
        "id": provider_id, "date": purchased_at.isoformat() if purchased_at else None,
        "total": total, "currency": currency, "discount": total_discount,
        "store": [store_id, store_name, store_address],
        "items": [repr(item) for item in items], "adjustments": [repr(item) for item in adjustments],
        "warnings": sorted(set(warnings)),
    }
    content_hash = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    return ProviderReceipt(
        provider_id=provider_id,
        fingerprint=hashlib.sha256(provider_id.encode()).hexdigest(),
        merchant_name="Lidl", content_hash=content_hash, purchased_at=purchased_at,
        store_id=store_id, store_name=store_name, store_address=store_address,
        total_minor=total, currency=currency,
        total_discount_minor=total_discount,
        validation_status="needs_review" if warnings else "valid",
        warnings=sorted(set(warnings)), items=items, adjustments=adjustments,
    )
