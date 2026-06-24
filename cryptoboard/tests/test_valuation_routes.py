"""C9 — Wertverlauf-Routen: history/stats/refresh. CoinGecko gemockt, Cache real."""
from __future__ import annotations

import pytest

from backend import client as cg
from backend import price_history_store as price_store

PREFIX = "/api/modules/cryptoboard"


def _buy(coin="bitcoin", qty=1.0, at="2020-01-01"):
    return {"coin_id": coin, "symbol": coin[:3].upper(), "name": coin.title(),
            "kind": "transfer_in", "quantity": qty, "price": 0.0, "executed_at": at}


@pytest.fixture
def mock_chart(monkeypatch):
    """market_chart liefert 3 Tage Kurse für jeden Coin."""
    async def fake_chart(coin_id, vs, days):
        base = {"bitcoin": 100.0, "ethereum": 10.0}.get(coin_id, 1.0)
        # 2020-01-01..03 (ms-Timestamps der Tagesanfänge UTC)
        return [
            [1577836800000, base],        # 2020-01-01
            [1577923200000, base * 1.1],  # 2020-01-02
            [1578009600000, base * 1.2],  # 2020-01-03
        ]
    monkeypatch.setattr(cg, "market_chart", fake_chart)


# ---------------------------------------------------------------- Auth
def test_history_braucht_auth(client):
    assert client.get(f"{PREFIX}/portfolio/history").status_code == 401


def test_stats_braucht_auth(client):
    assert client.get(f"{PREFIX}/portfolio/stats").status_code == 401


# ---------------------------------------------------------------- history
def test_history_leer_ohne_transaktionen(client, auth_headers, mock_chart):
    data = client.get(f"{PREFIX}/portfolio/history", headers=auth_headers).json()
    assert data["points"] == []
    assert data["currency"] == "EUR"


def test_history_berechnet_wertreihe(client, auth_headers, mock_chart):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(qty=2.0, at="2020-01-01"), headers=auth_headers)
    data = client.get(f"{PREFIX}/portfolio/history", headers=auth_headers).json()
    pts = data["points"]
    assert len(pts) >= 3
    assert pts[0]["day"] == "2020-01-01"
    assert pts[0]["value"] == pytest.approx(200.0)   # 2 BTC * 100
    assert pts[2]["value"] == pytest.approx(240.0)   # 2 BTC * 120


def test_history_cacht_kurse(client, auth_headers, mock_chart):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(at="2020-01-01"), headers=auth_headers)
    client.get(f"{PREFIX}/portfolio/history", headers=auth_headers)
    # Kurse sind jetzt im Cache
    assert "bitcoin" in price_store.have_coins()
    assert len(price_store.get_series("bitcoin")) == 3


def test_history_nutzt_cache_kein_zweiter_fetch(client, auth_headers, monkeypatch):
    calls = {"n": 0}

    async def counting_chart(coin_id, vs, days):
        calls["n"] += 1
        return [[1577836800000, 100.0]]

    monkeypatch.setattr(cg, "market_chart", counting_chart)
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(at="2020-01-01"), headers=auth_headers)
    client.get(f"{PREFIX}/portfolio/history", headers=auth_headers)
    client.get(f"{PREFIX}/portfolio/history", headers=auth_headers)
    assert calls["n"] == 1  # zweiter Aufruf aus dem Cache


# ---------------------------------------------------------------- stats
def test_stats_berechnet(client, auth_headers, mock_chart):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(qty=1.0, at="2020-01-01"), headers=auth_headers)
    s = client.get(f"{PREFIX}/portfolio/stats", headers=auth_headers).json()
    assert s["current"] == pytest.approx(120.0)       # Tag 3: 1 BTC * 120
    assert s["ath"]["value"] == pytest.approx(120.0)
    assert s["ath"]["day"] == "2020-01-03"
    assert s["currency"] == "EUR"


# ---------------------------------------------------------------- refresh
def test_refresh_laedt_coins(client, auth_headers, mock_chart):
    client.post(f"{PREFIX}/portfolio/transactions", json=_buy(coin="ethereum", at="2020-01-01"), headers=auth_headers)
    r = client.post(f"{PREFIX}/portfolio/history/refresh", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "ethereum" in price_store.have_coins()
