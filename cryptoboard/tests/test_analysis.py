"""C5 — Analyse-Routen: Indikatoren (Chart-Durchstich) + Sentiment, Clients gemockt."""
from __future__ import annotations

from backend import client as cg
from backend import sentiment as sent

PREFIX = "/api/modules/cryptoboard"


# ---------------------------------------------------------------- Auth-Gates
def test_indicators_braucht_auth(client):
    assert client.get(f"{PREFIX}/indicators/bitcoin").status_code == 401


def test_sentiment_braucht_auth(client):
    assert client.get(f"{PREFIX}/sentiment").status_code == 401


# ---------------------------------------------------------------- Validierung
def test_indicators_invalid_coin_id(client, auth_headers):
    r = client.get(f"{PREFIX}/indicators/Invalid_Id", headers=auth_headers)
    assert r.status_code == 400


def test_indicators_invalid_currency(client, auth_headers):
    r = client.get(f"{PREFIX}/indicators/bitcoin?vs=bad$", headers=auth_headers)
    assert r.status_code == 400


def test_indicators_invalid_days(client, auth_headers):
    r = client.get(f"{PREFIX}/indicators/bitcoin?days=abc", headers=auth_headers)
    assert r.status_code == 400


# ---------------------------------------------------------------- Durchstich
def test_indicators_durchstich(client, auth_headers, monkeypatch):
    # 60 synthetische Chart-Punkte [ts, price]
    chart = [[1000 + i * 86400000, float(i + 1)] for i in range(60)]

    async def fake_chart(coin_id, vs, days):
        return chart

    monkeypatch.setattr(cg, "market_chart", fake_chart)
    r = client.get(f"{PREFIX}/indicators/bitcoin?vs=eur&days=90", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["prices"]) == 60
    assert len(data["times"]) == 60
    assert "rsi14" in data and "macd" in data and "sma20" in data
    # steigende Reihe → RSI am Ende = 100
    assert data["rsi14"][-1] == 100.0


def test_indicators_leerer_chart(client, auth_headers, monkeypatch):
    async def fake_chart(coin_id, vs, days):
        return []

    monkeypatch.setattr(cg, "market_chart", fake_chart)
    r = client.get(f"{PREFIX}/indicators/bitcoin", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["prices"] == []


def test_sentiment_durchstich(client, auth_headers, monkeypatch):
    async def fake_fng(limit=1):
        return {
            "current": {"value": 64, "classification": "Greed", "timestamp": 1700000000},
            "history": [{"value": 64, "classification": "Greed", "timestamp": 1700000000}],
        }

    monkeypatch.setattr(sent, "fear_greed", fake_fng)
    r = client.get(f"{PREFIX}/sentiment?limit=30", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["current"]["value"] == 64
    assert data["current"]["classification"] == "Greed"


def test_sentiment_cache(client, auth_headers, monkeypatch):
    calls = 0

    async def fake_fng(limit=1):
        nonlocal calls
        calls += 1
        return {"current": {"value": 50, "classification": "Neutral", "timestamp": 1}, "history": []}

    monkeypatch.setattr(sent, "fear_greed", fake_fng)
    client.get(f"{PREFIX}/sentiment?limit=30", headers=auth_headers)
    client.get(f"{PREFIX}/sentiment?limit=30", headers=auth_headers)
    assert calls == 1  # zweiter Call aus dem Cache
