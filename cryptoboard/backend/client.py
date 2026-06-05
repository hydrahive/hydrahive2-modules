"""CoinGecko-Client — Kurse, Charts, Coin-Suche.

Keyless gegen die Public-API (niedrigeres Rate-Limit) oder mit Demo-Key aus
HH_COINGECKO_API_KEY (Header x-cg-demo-api-key). Alle Netz-Calls laufen durch
_get() — in Tests gemockt, kein echter Traffic.

Die Helfer liefern bereits aufbereitete, flache Dicts (nur die Felder, die das
Frontend braucht), nicht die rohen CoinGecko-Payloads.
"""
from __future__ import annotations

from typing import Any

import httpx
from hydrahive.settings.overrides import resolve

_BASE = "https://api.coingecko.com/api/v3"
_TIMEOUT = 15.0


def _key() -> str:
    return resolve("coingecko_api_key").strip()


def _headers() -> dict[str, str]:
    key = _key()
    return {"x-cg-demo-api-key": key} if key else {}


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        r = await http.get(f"{_BASE}{path}", params=params or {}, headers=_headers())
        r.raise_for_status()
        return r.json()


def _market_row(c: dict) -> dict:
    spark = (c.get("sparkline_in_7d") or {}).get("price") or []
    return {
        "id": c.get("id"),
        "symbol": (c.get("symbol") or "").upper(),
        "name": c.get("name"),
        "image": c.get("image"),
        "price": c.get("current_price"),
        "market_cap": c.get("market_cap"),
        "market_cap_rank": c.get("market_cap_rank"),
        "volume": c.get("total_volume"),
        "change_24h": c.get("price_change_percentage_24h_in_currency"),
        "change_7d": c.get("price_change_percentage_7d_in_currency"),
        "sparkline": spark,
    }


async def search(query: str) -> list[dict]:
    data = await _get("/search", {"query": query})
    coins = data.get("coins", []) if isinstance(data, dict) else []
    return [
        {
            "id": c.get("id"),
            "symbol": (c.get("symbol") or "").upper(),
            "name": c.get("name"),
            "market_cap_rank": c.get("market_cap_rank"),
            "thumb": c.get("thumb"),
        }
        for c in coins
    ]


async def markets(vs_currency: str, *, ids: list[str] | None = None, top: int | None = None) -> list[dict]:
    params: dict[str, Any] = {
        "vs_currency": vs_currency,
        "price_change_percentage": "24h,7d",
        "sparkline": "true",
    }
    if ids:
        params["ids"] = ",".join(ids)
    if top:
        params["order"] = "market_cap_desc"
        params["per_page"] = str(top)
        params["page"] = "1"
    data = await _get("/coins/markets", params)
    return [_market_row(c) for c in data] if isinstance(data, list) else []


async def market_chart(coin_id: str, vs_currency: str, days: str) -> list[list[float]]:
    data = await _get(f"/coins/{coin_id}/market_chart", {"vs_currency": vs_currency, "days": days})
    return data.get("prices", []) if isinstance(data, dict) else []


async def coin_detail(coin_id: str, vs_currency: str) -> dict:
    data = await _get(
        f"/coins/{coin_id}",
        {
            "localization": "false", "tickers": "false", "market_data": "true",
            "community_data": "false", "developer_data": "false", "sparkline": "false",
        },
    )
    if not isinstance(data, dict):
        return {}
    md = data.get("market_data") or {}

    def cur(field: dict | None) -> Any:
        return (field or {}).get(vs_currency)

    return {
        "id": data.get("id"),
        "symbol": (data.get("symbol") or "").upper(),
        "name": data.get("name"),
        "image": (data.get("image") or {}).get("large"),
        "price": cur(md.get("current_price")),
        "market_cap": cur(md.get("market_cap")),
        "market_cap_rank": md.get("market_cap_rank"),
        "volume": cur(md.get("total_volume")),
        "change_24h": md.get("price_change_percentage_24h"),
        "change_7d": md.get("price_change_percentage_7d"),
        "ath": cur(md.get("ath")),
        "atl": cur(md.get("atl")),
        "circulating_supply": md.get("circulating_supply"),
        "total_supply": md.get("total_supply"),
        "max_supply": md.get("max_supply"),
        "description": ((data.get("description") or {}).get("en") or "")[:500],
        "homepage": ((data.get("links") or {}).get("homepage") or [None])[0],
    }
