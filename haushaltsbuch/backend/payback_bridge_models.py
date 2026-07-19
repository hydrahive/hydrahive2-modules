"""Strict, bounded wire contract for the PAYBACK browser bridge."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import Request
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from .loyalty_models import ConnectionVisibility


class StrictBridgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PaybackBridgeStart(StrictBridgeModel):
    accepted_experimental_risk: Literal[True]
    alias: str | None = Field(default="PAYBACK", min_length=1, max_length=120)
    visibility: ConnectionVisibility = "owner"


class PaybackBalanceInput(StrictBridgeModel):
    observed_at: AwareDatetime
    available_points: int = Field(ge=0, le=2_000_000_000, strict=True)


class PaybackExpirationInput(StrictBridgeModel):
    expiration_date: date
    points: int = Field(gt=0, le=2_000_000_000, strict=True)
    status: Literal["scheduled", "expired", "cancelled"] = "scheduled"


class PaybackPartnerInput(StrictBridgeModel):
    provider_partner_id: str = Field(
        min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    name: str = Field(min_length=1, max_length=240)
    active: bool = True


class PaybackActivityInput(StrictBridgeModel):
    provider_activity_id: str | None = Field(
        default=None, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    activity_type: Literal["earn", "redeem", "expire", "reversal", "adjustment"]
    activity_date: date
    points_delta: int = Field(ge=-2_000_000_000, le=2_000_000_000, strict=True)
    partner_provider_id: str | None = Field(
        default=None, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    original_description: str | None = Field(default=None, max_length=2000)
    purchase_amount_minor: int | None = Field(
        default=None, ge=0, le=100_000_000_000, strict=True
    )
    purchase_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    provider_updated_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def purchase_money_is_complete(self):
        if (self.purchase_amount_minor is None) != (self.purchase_currency is None):
            raise ValueError("purchase amount and currency must be supplied together")
        return self


class PaybackCouponInput(StrictBridgeModel):
    provider_coupon_id: str | None = Field(
        default=None, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    partner_provider_id: str | None = Field(
        default=None, min_length=1, max_length=256, pattern=r"^[A-Za-z0-9._:-]+$"
    )
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=4000)
    valid_from: date | None = None
    valid_until: date | None = None
    activation_status: Literal[
        "available", "activated", "redeemed", "expired", "unavailable"
    ] = "available"
    multiplier: str | None = Field(default=None, min_length=1, max_length=40)
    bonus_points: int | None = Field(default=None, ge=0, le=2_000_000_000, strict=True)
    condition_text: str | None = Field(default=None, max_length=4000)
    provider_updated_at: AwareDatetime | None = None

    @field_validator("multiplier")
    @classmethod
    def multiplier_is_positive_decimal(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("multiplier must be numeric") from exc
        if not parsed.is_finite() or parsed <= 0:
            raise ValueError("multiplier must be a finite positive number")
        return value

    @model_validator(mode="after")
    def validity_is_ordered(self):
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must not precede valid_from")
        return self


MAX_IMPORT_BODY_BYTES = 8 * 1024 * 1024


class InvalidImportBody(ValueError):
    pass


class PaybackBridgeImport(StrictBridgeModel):
    pairing_code: str = Field(
        min_length=43, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )
    captured_at: AwareDatetime
    balance: PaybackBalanceInput | None = None
    expirations: list[PaybackExpirationInput] = Field(
        default_factory=list, max_length=100
    )
    partners: list[PaybackPartnerInput] = Field(default_factory=list, max_length=500)
    activities: list[PaybackActivityInput] = Field(
        default_factory=list, max_length=2000
    )
    coupons: list[PaybackCouponInput] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def contains_useful_data(self):
        if not (
            self.balance
            or self.expirations
            or self.partners
            or self.activities
            or self.coupons
        ):
            raise ValueError("at least one data record is required")
        return self


async def read_import_request(request: Request) -> PaybackBridgeImport:
    """Read a bounded body and hide validation details at the public endpoint."""
    content_type = (
        request.headers.get("content-type", "").partition(";")[0].strip().lower()
    )
    if content_type != "application/json":
        raise InvalidImportBody
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_IMPORT_BODY_BYTES:
                raise InvalidImportBody
        except ValueError as exc:
            raise InvalidImportBody from exc
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_IMPORT_BODY_BYTES:
            raise InvalidImportBody
        chunks.append(chunk)
    try:
        decoded = json.loads(b"".join(chunks).decode("utf-8"))
        return PaybackBridgeImport.model_validate(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise InvalidImportBody from exc
