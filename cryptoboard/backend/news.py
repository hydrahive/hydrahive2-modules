"""CryptoCompare (CCData) News-Client — Krypto-Schlagzeilen.

Keyless oder mit optionalem Free-Key aus HH_CRYPTOCOMPARE_API_KEY
(Header authorization: Apikey <key>). Liefert flache Dicts mit nur den
Frontend-relevanten Feldern; Body auf 600 Zeichen gekürzt.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

_URL = "https://min-api.cryptocompare.com/data/v2/news/"
_TIMEOUT = 15.0


def _key() -> str:
    return (os.environ.get("HH_CRYPTOCOMPARE_API_KEY") or "").strip()


def _headers() -> dict[str, str]:
    key = _key()
    return {"authorization": f"Apikey {key}"} if key else {}


async def _get(params: dict[str, Any]) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        r = await http.get(_URL, params=params, headers=_headers())
        r.raise_for_status()
        return r.json()


def _row(i: dict) -> dict:
    return {
        "id": i.get("id"),
        "title": i.get("title"),
        "url": i.get("url"),
        "source": (i.get("source_info") or {}).get("name") or i.get("source"),
        "body": (i.get("body") or "")[:600],
        "image": i.get("imageurl"),
        "published_at": i.get("published_on"),  # Unix-Timestamp
        "categories": i.get("categories"),
    }


async def latest(categories: str | None = None, lang: str = "EN") -> list[dict]:
    params: dict[str, Any] = {"lang": lang}
    if categories:
        params["categories"] = categories
    data = await _get(params)
    items = data.get("Data", []) if isinstance(data, dict) else []
    return [_row(i) for i in items if isinstance(i, dict)]
