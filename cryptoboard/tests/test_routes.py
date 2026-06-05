"""C1 — Markt-Routen: Auth-Gate, Validierung, Cache-Durchstich (Client gemockt)."""
from __future__ import annotations

from backend import client as cg

PREFIX = "/api/modules/cryptoboard"


def test_search_braucht_auth(client):
    r = client.get(f"{PREFIX}/search?q=bit")
    assert r.status_code == 401


def test_search_durchstich(client, auth_headers, monkeypatch):
    async def fake_search(q):
        return [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "market_cap_rank": 1, "thumb": "x"}]

    monkeypatch.setattr(cg, "search", fake_search)
    r = client.get(f"{PREFIX}/search?q=bit", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["id"] == "bitcoin"


def test_search_leer_ohne_query(client, auth_headers):
    r = client.get(f"{PREFIX}/search?q=", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_markets_lehnt_ungueltige_currency_ab(client, auth_headers):
    r = client.get(f"{PREFIX}/markets?ids=bitcoin&vs=invalid$", headers=auth_headers)
    assert r.status_code == 400


def test_chart_lehnt_ungueltige_coin_id_ab(client, auth_headers):
    # Großbuchstaben/Underscore matchen die id-Regex nicht → 400 vor Upstream-Call
    r = client.get(f"{PREFIX}/chart/Invalid_Id?vs=eur&days=7", headers=auth_headers)
    assert r.status_code == 400


def test_chart_durchstich(client, auth_headers, monkeypatch):
    async def fake_chart(coin_id, vs, days):
        return [[1000, 90], [2000, 91]]

    monkeypatch.setattr(cg, "market_chart", fake_chart)
    r = client.get(f"{PREFIX}/chart/bitcoin?vs=eur&days=7", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["prices"] == [[1000, 90], [2000, 91]]


def test_top_cache_verhindert_doppel_fetch(client, auth_headers, monkeypatch):
    calls = 0

    async def fake_markets(vs, *, ids=None, top=None):
        nonlocal calls
        calls += 1
        return []

    monkeypatch.setattr(cg, "markets", fake_markets)
    client.get(f"{PREFIX}/top?vs=eur&n=10", headers=auth_headers)
    client.get(f"{PREFIX}/top?vs=eur&n=10", headers=auth_headers)
    assert calls == 1  # zweiter Treffer aus dem Cache
