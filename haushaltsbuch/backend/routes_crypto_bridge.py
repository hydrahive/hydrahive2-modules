"""Endpunkte für die Crypto-Brücke (Phase 3)."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from . import crypto_addresses, crypto_bridge, crypto_holdings
from .access import Principal
from .crypto_bridge_models import CryptoAddressLinkCreate, CryptoLinkCreate, CryptoTradeImportRequest

router = APIRouter()


@router.get("/crypto-bridge/status")
def get_crypto_status(principal: Principal) -> dict:
    return crypto_bridge.get_status(principal)


@router.put("/accounts/{account_id}/crypto-link")
def link_crypto_account(account_id: int, body: CryptoLinkCreate, principal: Principal) -> dict:
    return crypto_bridge.link_account(account_id, body, principal)


@router.delete("/accounts/{account_id}/crypto-link")
def unlink_crypto_account(
    account_id: int, principal: Principal, revision: int = Query(ge=1)
) -> dict:
    return crypto_bridge.unlink_account(account_id, revision, principal)


@router.get("/accounts/{account_id}/crypto-value")
def get_crypto_value(account_id: int, principal: Principal) -> dict:
    return crypto_bridge.get_crypto_value(account_id, principal)


@router.post("/crypto-bridge/trade-imports", status_code=status.HTTP_201_CREATED)
def create_trade_import(body: CryptoTradeImportRequest, principal: Principal) -> dict:
    return crypto_bridge.preview_trade_import(body, principal)


@router.get("/crypto-bridge/addresses")
def get_crypto_addresses(principal: Principal) -> list[dict]:
    return crypto_addresses.get_addresses(principal)


@router.put("/accounts/{account_id}/crypto-addresses")
def link_crypto_addresses(account_id: int, body: CryptoAddressLinkCreate, principal: Principal) -> dict:
    return crypto_addresses.link_addresses(account_id, body, principal)


@router.delete("/accounts/{account_id}/crypto-addresses")
def unlink_crypto_addresses(
    account_id: int, principal: Principal, revision: int = Query(ge=1)
) -> dict:
    return crypto_addresses.unlink_addresses(account_id, revision, principal)


@router.get("/accounts/{account_id}/crypto-holdings")
def get_crypto_holdings(account_id: int, principal: Principal) -> dict:
    return crypto_holdings.get_crypto_holdings(account_id, principal)
