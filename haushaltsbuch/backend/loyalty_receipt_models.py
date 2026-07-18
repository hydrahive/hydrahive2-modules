"""Kanonische, providerneutrale Belegdaten ohne Rohpayloads."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

AdjustmentKind = Literal["discount", "coupon", "deposit", "rounding"]


@dataclass(frozen=True, slots=True)
class ProviderReceiptItem:
    sequence: int
    original_name: str
    gtin: str | None = None
    quantity: str | None = None
    unit: Literal["piece", "kg"] | None = None
    unit_price_minor: int | None = None
    total_minor: int | None = None
    tax_group: str | None = None
    is_return: bool = False


@dataclass(frozen=True, slots=True)
class ProviderReceiptAdjustment:
    kind: AdjustmentKind
    amount_minor: int
    description: str | None = None
    item_sequence: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderReceipt:
    provider_id: str
    fingerprint: str
    merchant_name: str
    content_hash: str
    purchased_at: datetime | None = None
    store_id: str | None = None
    store_name: str | None = None
    store_address: str | None = None
    total_minor: int | None = None
    currency: str | None = None
    total_discount_minor: int | None = None
    validation_status: Literal["valid", "needs_review"] = "valid"
    warnings: list[str] = field(default_factory=list)
    items: list[ProviderReceiptItem] = field(default_factory=list)
    adjustments: list[ProviderReceiptAdjustment] = field(default_factory=list)
