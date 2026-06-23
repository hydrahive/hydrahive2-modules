"""Analyse-Routen — /api/modules/cryptoboard/{indicators/{coin_id},sentiment}.

Technische Indikatoren (aus dem CoinGecko-Chart berechnet) und der Fear & Greed
Index. Login-pflichtig, TTL-gecacht. coin_id/vs/days werden vor dem Upstream-Call
validiert.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import cache, client, indicators, sentiment
from .validators import DAYS_RE, ID_RE, VS_RE

router = APIRouter()

_TTL_INDICATORS = 300.0
_TTL_SENTIMENT = 600.0
_DEFAULT_VS = "eur"

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _valid_id(coin_id: str) -> str:
    if not ID_RE.match(coin_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    return coin_id


def _valid_vs(vs: str) -> str:
    vs = vs.lower()
    if not VS_RE.match(vs):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_currency")
    return vs


def _valid_days(days: str) -> str:
    if not DAYS_RE.match(days):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_days")
    return days


async def _compute(coin_id: str, vs: str, days: str) -> dict:
    raw = await client.market_chart(coin_id, vs, days)
    # CoinGecko liefert [[ts, price], …]; wir brauchen Zeitstempel + Schlusskurse.
    times = [int(p[0]) for p in raw if isinstance(p, list) and len(p) >= 2]
    prices = [float(p[1]) for p in raw if isinstance(p, list) and len(p) >= 2]
    series = indicators.compute_all(prices)
    return {"times": times, "prices": prices, **series}


@router.get("/indicators/{coin_id}")
async def get_indicators(coin_id: str, auth: Auth, vs: str = _DEFAULT_VS, days: str = "90") -> dict:
    coin_id = _valid_id(coin_id)
    vs = _valid_vs(vs)
    days = _valid_days(days)
    key = f"indicators:{coin_id}:{vs}:{days}"
    return await cache.cached(key, _TTL_INDICATORS, lambda: _compute(coin_id, vs, days))


@router.get("/sentiment")
async def get_sentiment(auth: Auth, limit: int = 30) -> dict:
    limit = max(1, min(90, limit))
    key = f"sentiment:{limit}"
    return await cache.cached(key, _TTL_SENTIMENT, lambda: sentiment.fear_greed(limit))
