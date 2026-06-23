"""Portfolio-Routen — /api/modules/cryptoboard/portfolio[/transactions[/{id}]].

Manuelles Trade-Log (Buy/Sell/Transfer) + berechnete Holdings & P&L (FIFO, EUR).
Alle Routen erfordern Login; jede Operation ist strikt user-scoped. Kein
Wallet-/Exchange-Zugriff, kein Autotrading — reine manuelle Erfassung.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import portfolio, portfolio_store as store
from .validators import ID_RE, ISO_RE

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class TxIn(BaseModel):
    coin_id: str = Field(min_length=1, max_length=80)
    symbol: str = Field(default="", max_length=20)
    name: str = Field(default="", max_length=120)
    kind: str = Field(min_length=1, max_length=20)
    quantity: float = Field(gt=0)
    price: float = Field(default=0.0, ge=0)
    fee: float = Field(default=0.0, ge=0)
    executed_at: str = Field(min_length=1, max_length=40)
    note: str = Field(default="", max_length=500)


def _validated(body: TxIn) -> dict:
    coin_id = body.coin_id.strip().lower()
    if not ID_RE.match(coin_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    if body.kind not in store.KINDS:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_kind")
    if not ISO_RE.match(body.executed_at.strip()):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_date")
    return {
        "coin_id": coin_id,
        "symbol": body.symbol.strip().upper(),
        "name": body.name.strip(),
        "kind": body.kind,
        "quantity": body.quantity,
        "price": body.price,
        "fee": body.fee,
        "executed_at": body.executed_at.strip(),
        "note": body.note.strip(),
    }


@router.get("/portfolio")
async def get_portfolio(auth: Auth) -> dict:
    user, _ = auth
    return await portfolio.summary(user)


@router.get("/portfolio/coin/{coin_id}")
async def get_portfolio_coin(coin_id: str, auth: Auth) -> dict:
    user, _ = auth
    coin_id = coin_id.strip().lower()
    if not ID_RE.match(coin_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    return await portfolio.coin_detail(user, coin_id)


@router.get("/portfolio/transactions")
def list_transactions(auth: Auth, coin_id: str = "") -> list[dict]:
    user, _ = auth
    cid = coin_id.strip().lower() or None
    if cid and not ID_RE.match(cid):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    return store.list_for(user, coin_id=cid)


@router.get("/portfolio/transactions/count")
def count_transactions(auth: Auth, coin_id: str = "") -> dict:
    user, _ = auth
    cid = coin_id.strip().lower() or None
    if cid and not ID_RE.match(cid):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    return {"count": store.count_for(user, coin_id=cid)}


@router.delete("/portfolio/transactions")
def clear_transactions(auth: Auth, coin_id: str = "") -> dict:
    """Löscht ALLE Transaktionen des Users (optional nur eines Coins)."""
    user, _ = auth
    cid = coin_id.strip().lower() or None
    if cid and not ID_RE.match(cid):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    deleted = store.clear_all(user, coin_id=cid)
    return {"ok": True, "deleted": deleted}


@router.post("/portfolio/transactions")
def add_transaction(body: TxIn, auth: Auth) -> dict:
    user, _ = auth
    data = _validated(body)
    try:
        tx_id = store.add(user, **data)
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"ok": True, "id": tx_id}


@router.patch("/portfolio/transactions/{tx_id}")
def update_transaction(tx_id: int, body: TxIn, auth: Auth) -> dict:
    user, _ = auth
    data = _validated(body)
    # coin_id/symbol/name bleiben unverändert — nur die buchhalterischen Felder.
    try:
        ok = store.update(
            user, tx_id,
            kind=data["kind"], quantity=data["quantity"], price=data["price"],
            fee=data["fee"], executed_at=data["executed_at"], note=data["note"],
        )
    except ValueError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))
    if not ok:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return {"ok": True}


@router.delete("/portfolio/transactions/{tx_id}")
def delete_transaction(tx_id: int, auth: Auth) -> dict:
    user, _ = auth
    if not store.remove(user, tx_id):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return {"ok": True}
