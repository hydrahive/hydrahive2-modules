"""Watchlist-Routen — /api/modules/cryptoboard/watchlist (per-User CRUD)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import watchlist_store as store
from .validators import ID_RE

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class WatchIn(BaseModel):
    coin_id: str = Field(min_length=1, max_length=80)
    symbol: str = Field(default="", max_length=20)
    name: str = Field(default="", max_length=120)


@router.get("/watchlist")
def list_watchlist(auth: Auth) -> list[dict]:
    user, _ = auth
    return store.list_for(user)


@router.post("/watchlist")
def add_watchlist(body: WatchIn, auth: Auth) -> dict:
    user, _ = auth
    coin_id = body.coin_id.strip().lower()
    if not ID_RE.match(coin_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    try:
        store.add(user, coin_id, body.symbol.strip().upper(), body.name.strip())
    except ValueError:
        raise coded(status.HTTP_400_BAD_REQUEST, "watchlist_full")
    return {"ok": True}


@router.delete("/watchlist/{coin_id}")
def remove_watchlist(coin_id: str, auth: Auth) -> dict:
    user, _ = auth
    store.remove(user, coin_id.strip().lower())
    return {"ok": True}
