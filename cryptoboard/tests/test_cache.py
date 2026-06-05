"""C1 — TTL-Cache: Treffer innerhalb TTL, Refetch nach Ablauf, clear."""
from __future__ import annotations

from backend import cache


async def test_producer_nur_einmal_innerhalb_ttl(monkeypatch):
    t = [100.0]
    monkeypatch.setattr(cache, "_now", lambda: t[0])
    calls = 0

    async def producer():
        nonlocal calls
        calls += 1
        return "value"

    v1 = await cache.cached("k", 60, producer)
    t[0] = 130.0  # noch innerhalb TTL
    v2 = await cache.cached("k", 60, producer)
    assert v1 == v2 == "value"
    assert calls == 1


async def test_refetch_nach_ablauf(monkeypatch):
    t = [100.0]
    monkeypatch.setattr(cache, "_now", lambda: t[0])
    calls = 0

    async def producer():
        nonlocal calls
        calls += 1
        return calls

    await cache.cached("k", 60, producer)
    t[0] = 200.0  # TTL abgelaufen
    v = await cache.cached("k", 60, producer)
    assert v == 2
    assert calls == 2


async def test_clear_leert(monkeypatch):
    monkeypatch.setattr(cache, "_now", lambda: 100.0)
    calls = 0

    async def producer():
        nonlocal calls
        calls += 1
        return calls

    await cache.cached("k", 60, producer)
    cache.clear()
    await cache.cached("k", 60, producer)
    assert calls == 2
