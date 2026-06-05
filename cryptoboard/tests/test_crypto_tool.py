"""C4 — query_crypto_price Agent-Tool (Client gemockt, kein Netz)."""
from __future__ import annotations

from pathlib import Path

from hydrahive.tools.base import ToolContext

from backend import client, crypto_tool


def _ctx() -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id="u", workspace=Path("."))


async def test_liefert_kurse(monkeypatch):
    async def fake_markets(vs, *, ids=None, top=None):
        assert vs == "eur"
        assert ids == ["bitcoin"]
        return [{"id": "bitcoin", "name": "Bitcoin", "symbol": "BTC", "price": 90000,
                 "change_24h": 1.5, "change_7d": -3.2, "market_cap": 1_700_000}]

    monkeypatch.setattr(client, "markets", fake_markets)
    res = await crypto_tool.TOOL.execute({"coins": ["bitcoin"]}, _ctx())
    assert res.success
    assert "Bitcoin (BTC)" in res.output["data"]
    assert res.output["currency"] == "EUR"


async def test_leere_coins_fail():
    res = await crypto_tool.TOOL.execute({"coins": []}, _ctx())
    assert not res.success


async def test_filtert_ungueltige_ids(monkeypatch):
    captured = {}

    async def fake_markets(vs, *, ids=None, top=None):
        captured["ids"] = ids
        return []

    monkeypatch.setattr(client, "markets", fake_markets)
    await crypto_tool.TOOL.execute({"coins": ["bitcoin", "BAD ID!", "ethereum"]}, _ctx())
    assert captured["ids"] == ["bitcoin", "ethereum"]


async def test_alle_ids_ungueltig_fail():
    res = await crypto_tool.TOOL.execute({"coins": ["BAD!", "@#$"]}, _ctx())
    assert not res.success


async def test_client_fehler_wird_zu_fail(monkeypatch):
    async def boom(vs, *, ids=None, top=None):
        raise RuntimeError("network down")

    monkeypatch.setattr(client, "markets", boom)
    res = await crypto_tool.TOOL.execute({"coins": ["bitcoin"]}, _ctx())
    assert not res.success
    assert "fehlgeschlagen" in res.error.lower()
