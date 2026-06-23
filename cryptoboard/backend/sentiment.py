"""Fear & Greed Index — alternative.me (keyless, kein Auth).

Liefert den aktuellen Krypto-Sentiment-Wert (0–100) plus Klassifizierung und
optional eine kurze Historie. Flache Dicts wie die anderen Clients; Netz-Call
in _get() gekapselt (in Tests gemockt).
"""
from __future__ import annotations

from typing import Any

import httpx

_URL = "https://api.alternative.me/fng/"
_TIMEOUT = 15.0


async def _get(limit: int) -> Any:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        r = await http.get(_URL, params={"limit": limit, "format": "json"})
        r.raise_for_status()
        return r.json()


def _row(d: dict) -> dict:
    value = d.get("value")
    ts = d.get("timestamp")
    try:
        value = int(value) if value is not None else None
    except (TypeError, ValueError):
        value = None
    try:
        ts = int(ts) if ts is not None else None
    except (TypeError, ValueError):
        ts = None
    return {
        "value": value,
        "classification": d.get("value_classification"),
        "timestamp": ts,
    }


async def fear_greed(limit: int = 1) -> dict:
    """Aktueller Index (+ optional Historie). limit=1 → nur der heutige Wert."""
    limit = max(1, min(90, limit))
    data = await _get(limit)
    items = data.get("data", []) if isinstance(data, dict) else []
    rows = [_row(d) for d in items if isinstance(d, dict)]
    if not rows:
        return {"current": None, "history": []}
    return {"current": rows[0], "history": rows}
