"""Wertverlauf-Routen — /api/modules/cryptoboard/portfolio/{history,stats,history/refresh}.

Marktwert-Auswertung (EUR), kein P&L. Historische Kurse kommen aus dem
dauerhaften Cache; refresh lädt fehlende Coins einmalig von CoinGecko nach.
Login-pflichtig, user-scoped (Bestände); Kurs-Cache ist global.
"""
from __future__ import annotations

from datetime import date, timezone, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from hydrahive.api.middleware.auth import require_auth

from . import (
    price_history,
    price_history_store as price_store,
    portfolio_store as store,
    valuation,
)

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _today() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _user_coins(user: str) -> list[str]:
    return [c["coin_id"] for c in store.distinct_coins(user)]


def _load_prices(coin_ids: list[str]) -> dict[str, dict[str, float]]:
    return {cid: price_store.get_series(cid) for cid in coin_ids}


@router.get("/portfolio/history")
async def get_history(auth: Auth) -> dict:
    user, _ = auth
    coins = _user_coins(user)
    # Fehlende Coins einmalig nachladen (idempotent, nur unbekannte).
    await price_history.ensure_coins(coins)
    txs = store.list_for(user)
    prices = _load_prices(coins)
    series = valuation.value_series(txs, prices, _today())
    cached = price_store.have_coins()
    missing = [c for c in coins if c not in cached]
    return {
        "currency": "EUR",
        "points": series,
        "missing_prices": missing,  # Coins ohne Kursdaten (Chart unvollständig)
    }


@router.get("/portfolio/stats")
async def get_stats(auth: Auth) -> dict:
    user, _ = auth
    coins = _user_coins(user)
    await price_history.ensure_coins(coins)
    txs = store.list_for(user)
    prices = _load_prices(coins)
    series = valuation.value_series(txs, prices, _today())
    out = valuation.stats_from_series(series)
    out["currency"] = "EUR"
    return out


@router.post("/portfolio/history/refresh")
async def refresh_history(auth: Auth, force: bool = False) -> dict:
    """Historische Kurse für alle Coins des Users (nach)laden."""
    user, _ = auth
    coins = _user_coins(user)
    loaded = await price_history.ensure_coins(coins, force=force)
    return {"ok": True, "loaded": loaded, "coins": len(coins)}
