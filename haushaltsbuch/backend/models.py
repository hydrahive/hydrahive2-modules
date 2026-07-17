from __future__ import annotations

from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

Currency = str


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_currency: Currency = "EUR"
    timezone: str = "Europe/Berlin"
    create_default_categories: bool = True

    @field_validator("base_currency")
    @classmethod
    def currency(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency must be a three-letter ISO code")
        return value

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("unknown IANA timezone") from exc
        return value


class HouseholdUpdate(HouseholdCreate):
    revision: int = Field(ge=1)
    create_default_categories: bool = False


class RevisionIn(BaseModel):
    revision: int = Field(ge=1)


class MemberAdd(BaseModel):
    username: str = Field(min_length=1, max_length=128)


class OwnershipTransfer(BaseModel):
    member_id: int = Field(gt=0)
    revision: int = Field(ge=1)


class InviteCreate(BaseModel):
    expires_in_hours: Literal[24] = 24


class InviteAccept(BaseModel):
    code: str = Field(min_length=20, max_length=256)


class HouseholdDelete(BaseModel):
    confirmation: Literal["DELETE"]
    household_name: str


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: Literal[
        "checking",
        "savings",
        "cash",
        "credit_card",
        "wallet",
        "liability",
        "asset",
        "custom",
    ]
    owner_member_id: int | None = Field(default=None, gt=0)
    currency: str = "EUR"
    bank_identifier: str | None = Field(default=None, max_length=64)
    opening_balance: int = Field(default=0, strict=True)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return HouseholdCreate.currency(value)


class AccountUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: Literal[
        "checking",
        "savings",
        "cash",
        "credit_card",
        "wallet",
        "liability",
        "asset",
        "custom",
    ]
    owner_member_id: int | None = Field(default=None, gt=0)
    bank_identifier: str | None = Field(default=None, max_length=64)
    archived: bool = False
    revision: int = Field(ge=1)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["income", "expense"]
    parent_id: int | None = Field(default=None, gt=0)
    icon: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int = 0


class CategoryUpdate(CategoryCreate):
    archived: bool = False
    revision: int = Field(ge=1)


class PostingIn(BaseModel):
    account_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)
    original_amount: int = Field(strict=True)
    currency: str
    base_amount: int = Field(strict=True)
    exchange_rate: str | None = Field(default=None, pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    exchange_rate_date: date | None = None
    exchange_rate_source: str | None = Field(default=None, max_length=64)
    member_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def xor_target(self):
        if (self.account_id is None) == (self.category_id is None):
            raise ValueError("exactly one of account_id and category_id is required")
        return self

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return HouseholdCreate.currency(value)


class TransactionCreate(BaseModel):
    booking_date: date
    value_date: date | None = None
    counterparty: str | None = Field(default=None, max_length=240)
    purpose: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=4000)
    source: Literal["manual", "import", "receipt", "lidl_plus", "payback"] = "manual"
    postings: list[PostingIn] = Field(min_length=2, max_length=100)


class TransactionMetadataUpdate(BaseModel):
    booking_date: date
    value_date: date
    counterparty: str | None = Field(default=None, max_length=240)
    purpose: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=4000)
    revision: int = Field(ge=1)


class BudgetCreate(BaseModel):
    category_id: int | None = Field(default=None, gt=0)
    type: Literal["monthly", "monthly_rollover", "reserve", "one_time", "yearly"]
    amount: int = Field(ge=0, strict=True)
    start_date: date
    end_date: date
    warning_threshold: int = Field(default=80, ge=0, le=100)

    @model_validator(mode="after")
    def dates_ordered(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class BudgetUpdate(BudgetCreate):
    active: bool = True
    revision: int = Field(ge=1)


class PeriodClose(BaseModel):
    start_date: date
    end_date: date
    revision: int = Field(ge=1)


class RecurringCreate(BaseModel):
    kind: Literal["income", "expense"]
    account_id: int = Field(gt=0)
    category_id: int = Field(gt=0)
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval_count: int = Field(default=1, ge=1, le=365)
    next_due_date: date
    end_date: date | None = None
    anchor_day: int | None = Field(default=None, ge=1, le=31)
    amount: int = Field(ge=0, strict=True)
    tolerance: int = Field(default=0, ge=0, strict=True)
    counterparty: str | None = Field(default=None, max_length=240)
    cancellation_notice_days: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=4000)
    status: Literal["draft", "confirmed", "inactive"] = "confirmed"
    confidence: str = Field(default="1", pattern=r"^(?:0(?:\.\d+)?|1(?:\.0+)?)$")

    @model_validator(mode="after")
    def recurring_dates(self):
        if self.end_date and self.end_date < self.next_due_date:
            raise ValueError("end_date must not precede next_due_date")
        if self.frequency == "monthly" and self.anchor_day is None:
            self.anchor_day = self.next_due_date.day
        return self


class RecurringUpdate(RecurringCreate):
    revision: int = Field(ge=1)
