"""Cryptoboard-Markt-Routen — /api/modules/cryptoboard/{search,markets,top,chart,coin}.

Alle Routen erfordern Login (require_auth) — Marktdaten sind öffentlich, aber so
zählt nur eingeloggter Traffic gegen unser CoinGecko-Limit. Antworten laufen
durch den TTL-Cache. coin_id/vs/days werden validiert, bevor sie in Upstream-
URLs/Params fließen (kein Pfad-/Param-Schmuggel).
"""
from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import cache, client

router = APIRouter()

_TTL_SEARCH = 3600.0
_TTL_MARKETS = 60.0
_TTL_CHART = 300.0
_TTL_COIN = 300.0
_DEFAULT_VS = "eur"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
_VS_RE = re.compile(r"^[a-z]{2,10}$")
_DAYS_RE = re.compile(r"^(\d{1,5}|max)$")

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _valid_id(coin_id: str) -> str:
    if not _ID_RE.match(coin_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_coin_id")
    return coin_id


def _valid_vs(vs: str) -> str:
    vs = vs.lower()
    if not _VS_RE.match(vs):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_currency")
    return vs


def _valid_days(days: str) -> str:
    if not _DAYS_RE.match(days):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_days")
    return days


@router.get("/search")
async def search(auth: Auth, q: str = "") -> list[dict]:
    q = q.strip()
    if not q:
        return []
    return await cache.cached(f"search:{q.lower()}", _TTL_SEARCH, lambda: client.search(q))


@router.get("/markets")
async def markets(auth: Auth, ids: str = "", vs: str = _DEFAULT_VS) -> list[dict]:
    vs = _valid_vs(vs)
    id_list = [i.strip().lower() for i in ids.split(",") if i.strip()]
    id_list = [i for i in id_list if _ID_RE.match(i)]
    if not id_list:
        return []
    key = f"markets:{vs}:{','.join(sorted(id_list))}"
    return await cache.cached(key, _TTL_MARKETS, lambda: client.markets(vs, ids=id_list))


@router.get("/top")
async def top(auth: Auth, vs: str = _DEFAULT_VS, n: int = 10) -> list[dict]:
    vs = _valid_vs(vs)
    n = max(1, min(100, n))
    return await cache.cached(f"top:{vs}:{n}", _TTL_MARKETS, lambda: client.markets(vs, top=n))


@router.get("/chart/{coin_id}")
async def chart(coin_id: str, auth: Auth, vs: str = _DEFAULT_VS, days: str = "7") -> dict:
    coin_id = _valid_id(coin_id)
    vs = _valid_vs(vs)
    days = _valid_days(days)
    key = f"chart:{coin_id}:{vs}:{days}"
    prices = await cache.cached(key, _TTL_CHART, lambda: client.market_chart(coin_id, vs, days))
    return {"prices": prices}


@router.get("/coin/{coin_id}")
async def coin(coin_id: str, auth: Auth, vs: str = _DEFAULT_VS) -> dict:
    coin_id = _valid_id(coin_id)
    vs = _valid_vs(vs)
    return await cache.cached(f"coin:{coin_id}:{vs}", _TTL_COIN, lambda: client.coin_detail(coin_id, vs))
