"""Kryptex-Pool-API abrufen und normalisieren (öffentlich, ohne Schlüssel).

Endpunkte (OpenAPI unter pool.kryptex.com, verifiziert 03.10.2026):
- ``/api/v1/index``                     → alle Coins inkl. ``device_types``
- ``/{coin}/api/v1/pool/info``          → Gebühr, Netz-Hashrate, estimated_profit_day
- ``/api/v1/coin/{coin}/info``          → daily_emission (Fallback-Rechnung)
- ``/api/v1/coin/{coin}/price/chart``   → Kurs in USD (letzter Punkt)

Fehler einzelner Coins brechen den Abruf nicht ab — der Coin fehlt dann nur.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from .profit import CoinQuote, coins_per_hs_day

logger = logging.getLogger(__name__)

BASE = "https://pool.kryptex.com"
TIMEOUT = httpx.Timeout(15.0, connect=8.0)
HEADERS = {"User-Agent": "HydraHive-Mining/0.1"}
_COIN_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,23}$")
_PARALLEL = 4  # Kryptex nicht fluten


class KryptexError(RuntimeError):
    """Index nicht abrufbar — ohne Index gibt es keine Coin-Liste."""


async def _get(http: httpx.AsyncClient, path: str, **params: Any) -> Any:
    r = await http.get(f"{BASE}{path}", params=params or None)
    r.raise_for_status()
    return r.json()


def gpu_coins(index: dict) -> list[str]:
    """Ticker aller Coins, die Kryptex für GPUs anbietet (validiert)."""
    out = []
    for ticker, info in (index or {}).items():
        if not isinstance(info, dict) or "gpu" not in (info.get("device_types") or []):
            continue
        if _COIN_RE.match(str(ticker)):
            out.append(str(ticker))
    return sorted(out)


def _fee(pool: dict) -> tuple[float, str]:
    fee_type = str(pool.get("fee_type") or "PPS+")
    fee = pool.get("fee")
    if fee is None:
        fee = (pool.get("commission") or {}).get(fee_type, 0.0)
    return float(fee or 0.0), fee_type


async def _quote(http: httpx.AsyncClient, coin: str, sem: asyncio.Semaphore) -> CoinQuote | None:
    async with sem:
        try:
            pool = await _get(http, f"/{coin}/api/v1/pool/info")
            fee, fee_type = _fee(pool)
            kv = pool.get("estimated_profit_day")
            emission = None
            if not kv:
                emission = (await _get(http, f"/api/v1/coin/{coin}/info")).get("daily_emission")
            per_hs, estimated = coins_per_hs_day(
                kryptex_value=kv, daily_emission=emission,
                net_hashrate=pool.get("net_hashrate"), fee=fee,
            )
            chart = await _get(http, f"/api/v1/coin/{coin}/price/chart", time_range="day")
            price = float(chart[-1]["price"]) if chart else None
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
            logger.warning("Kryptex: Coin %s nicht abrufbar: %s", coin, exc)
            return None
    return CoinQuote(
        coin=coin, name=str(pool.get("name") or coin.upper()), algo=str(pool.get("algo") or "?"),
        fee=fee, fee_type=fee_type, profit_per_hs_day=per_hs, price_usd=price, estimated=estimated,
    )


async def fetch_quotes(client: httpx.AsyncClient | None = None) -> list[CoinQuote]:
    """Alle GPU-Coins abrufen. KryptexError nur, wenn schon der Index fehlt."""
    own = client is None
    http = client or httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS)
    try:
        try:
            index = await _get(http, "/api/v1/index")
        except (httpx.HTTPError, ValueError) as exc:
            raise KryptexError(f"index: {exc}") from exc
        sem = asyncio.Semaphore(_PARALLEL)
        results = await asyncio.gather(*(_quote(http, c, sem) for c in gpu_coins(index)))
        return [q for q in results if q is not None]
    finally:
        if own:
            await http.aclose()
