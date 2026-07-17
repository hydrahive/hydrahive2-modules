from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CsvColumnMapping(BaseModel):
    booking_date: str = Field(min_length=1, max_length=200)
    amount: str | None = Field(default=None, min_length=1, max_length=200)
    debit_amount: str | None = Field(default=None, min_length=1, max_length=200)
    credit_amount: str | None = Field(default=None, min_length=1, max_length=200)
    value_date: str | None = Field(default=None, min_length=1, max_length=200)
    currency: str | None = Field(default=None, min_length=1, max_length=200)
    counterparty: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = Field(default=None, min_length=1, max_length=200)
    bank_reference: str | None = Field(default=None, min_length=1, max_length=200)
    counterparty_identifier: str | None = Field(default=None, min_length=1, max_length=200)
    category_hint: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def amount_columns(self):
        if bool(self.amount) == bool(self.debit_amount and self.credit_amount):
            raise ValueError("map either amount or debit and credit")
        return self


class ImportProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    delimiter: Literal[";", ",", "\t"] = ";"
    encoding: Literal["utf-8", "utf-8-sig", "cp1252", "iso-8859-1"] = "utf-8"
    decimal_separator: Literal[".", ","] = ","
    date_format: str = Field(default="%d.%m.%Y", min_length=1, max_length=40)
    mapping: CsvColumnMapping


class ImportProfileUpdate(ImportProfileCreate):
    revision: int = Field(ge=1)


class ImportRowUpdate(BaseModel):
    revision: int = Field(ge=1)
    status: Literal["pending", "accepted", "rejected"] | None = None
    category_id: int | None = Field(default=None, gt=0)
    booking_date: date | None = None
    value_date: date | None = None
    amount_minor: int | None = None
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    counterparty: str | None = Field(default=None, max_length=240)
    purpose: str | None = Field(default=None, max_length=500)


class ImportComplete(BaseModel):
    revision: int = Field(ge=1)


class ImportReverse(BaseModel):
    revision: int = Field(ge=1)
