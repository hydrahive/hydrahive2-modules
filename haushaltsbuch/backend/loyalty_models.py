from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

LoyaltyProvider = Literal["lidl_plus", "payback"]
ConnectionVisibility = Literal["owner", "household"]
ConnectionStatus = Literal[
    "disconnected",
    "active",
    "syncing",
    "reauth_required",
    "blocked",
    "disabled",
    "error",
]
RemoteStatus = Literal["active", "gone"]

class ProviderCapabilities(BaseModel):
    receipts: bool = False
    receipt_items: bool = False
    discounts: bool = False
    deposits: bool = False
    balance: bool = False
    expirations: bool = False
    activities: bool = False
    coupons: bool = False
    partners: bool = False
    scheduled_sync: bool = False
    token_refresh: bool = False
    remote_revoke: bool = False

class LoyaltyConnection(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    provider: LoyaltyProvider
    owner_member_id: int = Field(gt=0)
    credential_ref: str = Field(min_length=1, max_length=500)
    account_fingerprint: str = Field(min_length=1, max_length=256)
    masked_account: str = Field(min_length=1, max_length=120)
    alias: str | None = Field(default=None, min_length=1, max_length=120)
    country_code: str = Field(default="DE", pattern=r"^[A-Z]{2}$")
    language_code: str = Field(default="de", min_length=2, max_length=16)
    visibility: ConnectionVisibility = "owner"
    status: ConnectionStatus = "disconnected"
    capabilities: ProviderCapabilities = Field(default_factory=ProviderCapabilities)
    feature_enabled: bool = False
    sync_enabled: bool = False
    sync_interval_hours: int | None = Field(default=None, gt=0)
    sync_cursor: str | None = None
    last_sync_at: datetime | None = None
    last_success_at: datetime | None = None
    next_sync_at: datetime | None = None
    last_error_code: str | None = Field(default=None, min_length=1, max_length=120)
    revision: int = Field(default=1, ge=1)
    created_at: datetime | None = None
    updated_at: datetime | None = None

class LoyaltySyncRun(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    connection_id: int = Field(gt=0)
    trigger: Literal["manual", "scheduled"]
    started_at: datetime
    finished_at: datetime | None = None
    status: Literal["running", "succeeded", "partial", "failed", "cancelled"] = "running"
    cursor_before: str | None = None
    cursor_after: str | None = None
    fetched_count: int = Field(default=0, ge=0, strict=True)
    created_count: int = Field(default=0, ge=0, strict=True)
    updated_count: int = Field(default=0, ge=0, strict=True)
    skipped_count: int = Field(default=0, ge=0, strict=True)
    error_code: str | None = Field(default=None, min_length=1, max_length=120)
    next_allowed_attempt_at: datetime | None = None

    @model_validator(mode="after")
    def completion_is_consistent(self):
        if (self.status == "running") != (self.finished_at is None):
            raise ValueError("only a running sync may omit finished_at")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self

class LoyaltyBalance(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    connection_id: int = Field(gt=0)
    observed_at: datetime
    available_points: int = Field(ge=0, strict=True)
    money_value_minor: int | None = Field(default=None, ge=0, strict=True)
    money_value_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    valuation_version: str | None = Field(default=None, min_length=1, max_length=120)
    fingerprint: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def complete_valuation(self):
        values = (self.money_value_minor, self.money_value_currency, self.valuation_version)
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("money valuation fields must be supplied together")
        return self

class LoyaltyPartner(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    provider: LoyaltyProvider
    provider_partner_id: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=240)
    active: bool = True
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    @model_validator(mode="after")
    def seen_times_are_ordered(self):
        if (
            self.first_seen_at is not None
            and self.last_seen_at is not None
            and self.last_seen_at < self.first_seen_at
        ):
            raise ValueError("last_seen_at must not precede first_seen_at")
        return self

class LoyaltyActivity(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    connection_id: int = Field(gt=0)
    provider_activity_id: str | None = Field(default=None, min_length=1, max_length=256)
    fingerprint: str = Field(min_length=1, max_length=256)
    activity_type: Literal["earn", "redeem", "expire", "reversal", "adjustment"]
    activity_date: date
    points_delta: int = Field(strict=True)
    partner_id: int | None = Field(default=None, gt=0)
    original_description: str | None = Field(default=None, max_length=2000)
    purchase_amount_minor: int | None = Field(default=None, ge=0, strict=True)
    purchase_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    provider_updated_at: datetime | None = None

    @model_validator(mode="after")
    def complete_purchase_amount(self):
        if (self.purchase_amount_minor is None) != (self.purchase_currency is None):
            raise ValueError("purchase amount and currency must be supplied together")
        return self
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    remote_status: RemoteStatus = "active"

class LoyaltyExpiration(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    connection_id: int = Field(gt=0)
    expiration_date: date
    points: int = Field(gt=0, strict=True)
    status: Literal["scheduled", "expired", "cancelled"] = "scheduled"
    provider_updated_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

class LoyaltyCoupon(BaseModel):
    id: int = Field(gt=0)
    household_id: int = Field(gt=0)
    connection_id: int = Field(gt=0)
    provider_coupon_id: str | None = Field(default=None, min_length=1, max_length=256)
    fingerprint: str = Field(min_length=1, max_length=256)
    partner_id: int | None = Field(default=None, gt=0)
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=4000)
    valid_from: date | None = None
    valid_until: date | None = None
    activation_status: Literal[
        "available", "activated", "redeemed", "expired", "unavailable"
    ] = "available"
    multiplier: str | None = Field(default=None, min_length=1, max_length=40)
    bonus_points: int | None = Field(default=None, ge=0, strict=True)
    condition_text: str | None = Field(default=None, max_length=4000)
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    provider_updated_at: datetime | None = None
    remote_status: RemoteStatus = "active"

    @field_validator("multiplier")
    @classmethod
    def multiplier_is_decimal(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                parsed = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError("multiplier must be numeric") from exc
            if not parsed.is_finite() or parsed <= 0:
                raise ValueError("multiplier must be a finite positive number")
        return value

    @model_validator(mode="after")
    def validity_is_ordered(self):
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until < self.valid_from
        ):
            raise ValueError("valid_until must not precede valid_from")
        return self
