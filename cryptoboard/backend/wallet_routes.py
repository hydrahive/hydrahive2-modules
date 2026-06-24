"""Wallet-Routen — /api/modules/cryptoboard/wallets[...].

Adress-Verwaltung (mehrere pro Chain) + aktuelle On-Chain-Bestände in EUR.
Login-pflichtig, strikt user-scoped. Nur Lesen on-chain — keine Keys.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import addresses_store as store, wallets
from .address_validators import is_valid_address, is_valid_chain

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class AddressIn(BaseModel):
    chain: str = Field(min_length=1, max_length=20)
    address: str = Field(min_length=1, max_length=120)
    label: str = Field(default="", max_length=60)


@router.get("/wallets")
def list_addresses(auth: Auth) -> list[dict]:
    user, _ = auth
    return store.list_for(user)


@router.post("/wallets")
def add_address(body: AddressIn, auth: Auth) -> dict:
    user, _ = auth
    chain = body.chain.strip().lower()
    address = body.address.strip()
    if not is_valid_chain(chain):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_chain")
    if not is_valid_address(chain, address):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_address")
    try:
        addr_id = store.add(user, chain, address, body.label.strip())
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"ok": True, "id": addr_id}


@router.delete("/wallets/{addr_id}")
def remove_address(addr_id: int, auth: Auth) -> dict:
    user, _ = auth
    if not store.remove(user, addr_id):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return {"ok": True}


@router.get("/wallets/balances")
async def get_balances(auth: Auth) -> dict:
    user, _ = auth
    return await wallets.balances(user)
