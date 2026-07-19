"""Defensive Normalisierung deutscher Lidl-Belege in kanonische Dataclasses."""
from __future__ import annotations

import hashlib
import json

from . import lidl_normalize_values as values
from .lidl_adjustments import append_coupons, normalize_adjustment
from .lidl_html_receipt import parse_html_items
from .loyalty_provider import InvalidProviderData
from .loyalty_receipt_models import ProviderReceipt, ProviderReceiptItem


_MAX_ITEMS = 1000
_MAX_ADJUSTMENTS = 2000
_MAX_SIGNED = 2**63 - 1
_INFO_WARNINGS = frozenset({
    "currency_inferred_de", "timezone_inferred_de", "total_discount_derived",
    "coupon_metadata_without_amount", "invalid_gtin",
})


def _item(raw: dict, sequence: int, warnings: list[str], adjustment_limit: int):
    name = values.bounded_text(raw.get("name"), 1000, warnings, "item_name_truncated")
    if name is None:
        name = "Unbekannter Artikel"
        warnings.append("missing_item_name")
    code, gtin = raw.get("codeInput"), values.valid_gtin(raw.get("codeInput"))
    if code and gtin is None and raw.get("_html_source") is not True:
        warnings.append("invalid_gtin")
    quantity_input = raw.get("quantity")
    quantity = values.decimal_value("1" if quantity_input is None else quantity_input)
    if quantity_input is not None and quantity is None:
        warnings.append("invalid_quantity")
    unit_price_value = values.decimal_value(raw.get("currentUnitPrice"))
    if raw.get("currentUnitPrice") is not None and unit_price_value is None:
        warnings.append("invalid_unit_price")
    unit_price = values.minor_value(unit_price_value)
    total = values.minor_value(raw.get("originalAmount"))
    if total is None and quantity is not None and unit_price_value is not None:
        total = values.minor_value(quantity * unit_price_value)
    is_weight = raw.get("isWeight") is True or bool(
        raw.get("_html_source") is True and quantity is not None
        and quantity != quantity.to_integral_value()
    )
    is_return = bool((quantity is not None and quantity < 0) or (total is not None and total < 0))
    item = ProviderReceiptItem(
        sequence=sequence, original_name=name, gtin=gtin,
        quantity=format(quantity, "f") if quantity is not None else None,
        unit="kg" if is_weight else "piece",
        unit_price_minor=unit_price, total_minor=total,
        tax_group=values.bounded_text(
            raw.get("taxGroupName") or raw.get("taxGroup"), 120, warnings,
            "tax_group_truncated",
        ), is_return=is_return,
    )
    adjustments = []
    discounts = raw.get("discounts") or []
    if not isinstance(discounts, list):
        discounts = []
        warnings.append("invalid_discounts")
    if len(discounts) > adjustment_limit:
        warnings.append("adjustment_limit")
    for discount in discounts[:adjustment_limit]:
        adjustment = normalize_adjustment(discount, "discount", sequence)
        if adjustment:
            adjustments.append(adjustment)
        else:
            warnings.append("invalid_discount")
    deposit = normalize_adjustment(raw.get("deposit"), "deposit", sequence)
    if deposit:
        if len(adjustments) < adjustment_limit:
            adjustments.append(deposit)
        else:
            warnings.append("adjustment_limit")
    return item, adjustments


def normalize_receipt(payload: dict) -> ProviderReceipt:
    if not isinstance(payload, dict):
        raise InvalidProviderData("receipt_id_missing")
    provider_id = str(payload.get("id") or "").strip()
    if not provider_id or len(provider_id) > 256:
        raise InvalidProviderData("receipt_id_missing")
    warnings: list[str] = []
    total_data = next(
        (payload.get(key) for key in ("totalAmount", "total", "ticketTotal", "amount")
         if payload.get(key) is not None),
        None,
    )
    total = values.minor_value(total_data)
    raw_currency = payload.get("currency")
    direct_currency = values.currency_code(raw_currency)
    nested_currency = values.currency_code(total_data) if isinstance(total_data, dict) else None
    raw_currency_present = raw_currency not in (None, "", {})
    nested_currency_present = isinstance(total_data, dict) and any(
        key in total_data for key in ("code", "currency", "currencyCode", "isoCode")
    )
    invalid_currency = (raw_currency_present and direct_currency is None) or (
        nested_currency_present and nested_currency is None
    )
    if invalid_currency:
        warnings.append("invalid_currency")
    if direct_currency and nested_currency and direct_currency != nested_currency:
        currency = None
        warnings.append("currency_conflict")
    else:
        currency = direct_currency or nested_currency
    if invalid_currency and raw_currency_present and nested_currency_present:
        currency = None
    if currency is None and not (raw_currency_present or nested_currency_present):
        currency = "EUR"
        warnings.append("currency_inferred_de")
    purchased_at = values.iso_datetime(payload.get("date"))
    if purchased_at is not None:
        purchased_at, timezone_warning = values.localize_german_time(purchased_at)
        if timezone_warning:
            warnings.append(timezone_warning)
    if total is None:
        warnings.append("missing_total")
    if purchased_at is None:
        warnings.append("missing_date")
    raw_items = payload.get("itemsLine")
    if not isinstance(raw_items, list) or not raw_items:
        raw_items = parse_html_items(payload.get("htmlPrintedReceipt"), warnings)
    if len(raw_items) > _MAX_ITEMS:
        warnings.append("item_limit")
        raw_items = raw_items[:_MAX_ITEMS]
    items, adjustments = [], []
    for sequence, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            warnings.append("invalid_item")
            continue
        remaining = max(0, _MAX_ADJUSTMENTS - len(adjustments))
        item, item_adjustments = _item(raw, sequence, warnings, remaining)
        items.append(item)
        adjustments.extend(item_adjustments)
    append_coupons(
        payload.get("couponsUsed"), adjustments, warnings, _MAX_ADJUSTMENTS,
    )
    store = payload.get("store") if isinstance(payload.get("store"), dict) else {}
    total_discount_data = payload.get("totalDiscount")
    total_discount = values.minor_value(total_discount_data)
    if total_discount_data is not None and total_discount is None:
        warnings.append("invalid_total_discount")
    total_discount = abs(total_discount) if total_discount is not None else None
    if total_discount is None:
        derived_discount = sum(
            -entry.amount_minor for entry in adjustments
            if entry.kind in ("discount", "coupon") and entry.amount_minor < 0
        )
        if 0 < derived_discount <= _MAX_SIGNED:
            total_discount = derived_discount
            warnings.append("total_discount_derived")
        elif derived_discount > _MAX_SIGNED:
            warnings.append("total_discount_out_of_range")
    store_id = values.bounded_text(store.get("id"), 256, warnings, "store_id_truncated")
    store_name = values.bounded_text(store.get("name"), 240, warnings, "store_name_truncated")
    store_address = values.bounded_text(store.get("address"), 1000, warnings, "store_address_truncated")
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
        validation_status=(
            "needs_review" if set(warnings) - _INFO_WARNINGS else "valid"
        ),
        warnings=sorted(set(warnings)), items=items, adjustments=adjustments,
    )
