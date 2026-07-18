"""Normalisierung und begrenzte Deduplizierung von Lidl-Beleganpassungen."""
from __future__ import annotations

from collections import Counter

from . import lidl_normalize_values as values
from .loyalty_receipt_models import ProviderReceiptAdjustment

_MAX_COUPON_INPUTS = 4000


def normalize_adjustment(
    raw, kind: str, sequence: int,
) -> ProviderReceiptAdjustment | None:
    if raw is None:
        return None
    data = raw if isinstance(raw, dict) else {"amount": raw}
    amount = values.minor_value(data)
    if amount is None:
        return None
    if kind in ("discount", "coupon"):
        amount = -abs(amount)
    description = data.get("description") or data.get("name") or data.get("title")
    description = str(description).strip()[:1000] if description else None
    return ProviderReceiptAdjustment(kind, amount, description, sequence)


def append_coupons(
    raw_coupons, adjustments: list[ProviderReceiptAdjustment],
    warnings: list[str], max_adjustments: int,
) -> None:
    coupons = raw_coupons or []
    if not isinstance(coupons, list):
        warnings.append("invalid_coupons")
        return
    html_adjustments = Counter(
        (entry.amount_minor, (entry.description or "").strip().casefold())
        for entry in adjustments if entry.kind == "discount"
    )
    for raw in coupons[:_MAX_COUPON_INPUTS]:
        adjustment = normalize_adjustment(raw, "coupon", -1)
        key = None if adjustment is None else (
            adjustment.amount_minor, (adjustment.description or "").strip().casefold()
        )
        if key is not None and html_adjustments[key] > 0:
            html_adjustments[key] -= 1
        elif adjustment is None:
            warnings.append("coupon_amount_unknown")
        elif len(adjustments) < max_adjustments:
            adjustments.append(adjustment)
        else:
            warnings.append("adjustment_limit")
            break
    if len(coupons) > _MAX_COUPON_INPUTS:
        warnings.append("adjustment_limit")
