"""Mini-TTL-Cache für CoinGecko-Antworten — schont das Free-Tier-Limit.

In-Memory, pro Prozess. Bei parallelen Anfragen auf denselben kalten Key kann
der Fetch doppelt laufen (kein Lock) — akzeptabel, GET ist idempotent. Wenige
Keys, vernachlässigbarer Speicher.
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

_store: dict[str, tuple[float, Any]] = {}


def _now() -> float:
    return time.monotonic()


async def cached(key: str, ttl: float, producer: Callable[[], Awaitable[Any]]) -> Any:
    hit = _store.get(key)
    if hit is not None and hit[0] > _now():
        return hit[1]
    value = await producer()
    _store[key] = (_now() + ttl, value)
    return value


def clear() -> None:
    _store.clear()
