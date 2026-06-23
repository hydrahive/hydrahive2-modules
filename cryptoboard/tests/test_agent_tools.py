"""C7 — Agent-Tools query_portfolio + query_crypto_analysis (Clients gemockt)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.tools.base import ToolContext

from backend import analysis_tool, client, portfolio_store, portfolio_tool, sentiment


def _ctx(user="testuser") -> ToolContext:
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=Path("."))


# ---------------------------------------------------------------- query_portfolio
@pytest.fixture
def mock_markets(monkeypatch):
    async def fake_markets(vs, *, ids=None, top=None):
        prices = {"bitcoin": {"id": "bitcoin", "price": 50000.0, "image": "x", "change_24h": 1.0}}
        return [prices[i] for i in (ids or []) if i in prices]
    monkeypatch.setattr(client, "markets", fake_markets)


@pytest.mark.asyncio
async def test_query_portfolio_leer(mock_markets):
    res = await portfolio_tool.TOOL.execute({}, _ctx())
    assert res.success
    assert res.output["count"] == 0


@pytest.mark.asyncio
async def test_query_portfolio_mit_position(mock_markets):
    portfolio_store.add(
        "testuser", coin_id="bitcoin", symbol="BTC", name="Bitcoin",
        kind="buy", quantity=1.0, price=40000.0, fee=0.0,
        executed_at="2026-01-01", note="",
    )
    res = await portfolio_tool.TOOL.execute({}, _ctx())
    assert res.success
    assert res.output["open_positions"] == 1
    assert "BTC" in res.output["data"]
    assert "Gesamtwert" in res.output["summary"]


@pytest.mark.asyncio
async def test_query_portfolio_isolation(mock_markets):
    portfolio_store.add(
        "testuser", coin_id="bitcoin", symbol="BTC", name="Bitcoin",
        kind="buy", quantity=1.0, price=40000.0, fee=0.0,
        executed_at="2026-01-01", note="",
    )
    # anderer User sieht nichts
    res = await portfolio_tool.TOOL.execute({}, _ctx(user="other"))
    assert res.success
    assert res.output["count"] == 0


# ---------------------------------------------------------------- query_crypto_analysis
@pytest.mark.asyncio
async def test_analysis_invalid_coin():
    res = await analysis_tool.TOOL.execute({"coin": "BAD ID!"}, _ctx())
    assert not res.success


@pytest.mark.asyncio
async def test_analysis_zu_wenig_daten(monkeypatch):
    async def fake_chart(coin, vs, days):
        return [[i, float(i)] for i in range(10)]
    monkeypatch.setattr(client, "market_chart", fake_chart)
    res = await analysis_tool.TOOL.execute({"coin": "bitcoin"}, _ctx())
    assert not res.success


@pytest.mark.asyncio
async def test_analysis_liefert_report(monkeypatch):
    async def fake_chart(coin, vs, days):
        return [[i, float(i + 1)] for i in range(90)]  # steigend

    async def fake_fng(limit=1):
        return {"current": {"value": 72, "classification": "Greed", "timestamp": 1}, "history": []}

    monkeypatch.setattr(client, "market_chart", fake_chart)
    monkeypatch.setattr(sentiment, "fear_greed", fake_fng)
    res = await analysis_tool.TOOL.execute({"coin": "bitcoin"}, _ctx())
    assert res.success
    assert res.output["coin"] == "bitcoin"
    assert "RSI" in res.output["analysis"]
    assert "72" in res.output["fear_greed"]


@pytest.mark.asyncio
async def test_analysis_chart_fehler_wird_fail(monkeypatch):
    async def boom(coin, vs, days):
        raise RuntimeError("down")
    monkeypatch.setattr(client, "market_chart", boom)
    res = await analysis_tool.TOOL.execute({"coin": "bitcoin"}, _ctx())
    assert not res.success
