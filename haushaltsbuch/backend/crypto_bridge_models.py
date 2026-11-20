"""Pydantic-DTOs für die Crypto-Brücke (Phase 3)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CryptoLinkCreate(BaseModel):
    portfolio_id: str = Field(min_length=1, max_length=120)
    revision: int = Field(ge=1)


class CryptoTradeImportRequest(BaseModel):
    wallet_account_id: int = Field(gt=0)
    fiat_account_id: int = Field(gt=0)
    fee_category_id: int | None = Field(default=None, gt=0)
    since: date | None = None


class CryptoAddressLinkCreate(BaseModel):
    """PUT /accounts/{id}/crypto-addresses (v2, VERTRAG-PORT-V2.md): ersetzt
    die Adressliste eines Wallet-Kontos."""

    address_ids: list[int] = Field(min_length=1)
    revision: int = Field(ge=1)
