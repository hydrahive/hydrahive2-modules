"""C6 — Alert-Regeln (CRUD, Isolation), Poller-Auslösung, Event-Historie.

Client/Portfolio gemockt — kein echter Netz-Traffic.
"""
from __future__ import annotations

import pytest

from backend import alert_poller
from backend import client as cg

PREFIX = "/api/modules/cryptoboard"


@pytest.fixture
def other_headers(client):
    r = client.post("/api/auth/login", json={"username": "other", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _alert(kind="price_above", coin="bitcoin", symbol="BTC", threshold=100000.0, **kw):
    return {"kind": kind, "coin_id": coin, "symbol": symbol, "threshold": threshold, **kw}


# ---------------------------------------------------------------- CRUD + Auth
def test_alerts_braucht_auth(client):
    assert client.get(f"{PREFIX}/alerts").status_code == 401


def test_add_list_delete_alert(client, auth_headers):
    assert client.get(f"{PREFIX}/alerts", headers=auth_headers).json() == []
    r = client.post(f"{PREFIX}/alerts", json=_alert(), headers=auth_headers)
    assert r.status_code == 200
    aid = r.json()["id"]

    items = client.get(f"{PREFIX}/alerts", headers=auth_headers).json()
    assert len(items) == 1
    assert items[0]["kind"] == "price_above"
    assert items[0]["active"] == 1

    assert client.delete(f"{PREFIX}/alerts/{aid}", headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/alerts", headers=auth_headers).json() == []


def test_toggle_active(client, auth_headers):
    aid = client.post(f"{PREFIX}/alerts", json=_alert(), headers=auth_headers).json()["id"]
    assert client.patch(f"{PREFIX}/alerts/{aid}", json={"active": False}, headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/alerts", headers=auth_headers).json()[0]["active"] == 0


def test_portfolio_alert_braucht_keine_coin_id(client, auth_headers):
    r = client.post(f"{PREFIX}/alerts", json={"kind": "portfolio_above", "threshold": 10000.0}, headers=auth_headers)
    assert r.status_code == 200


def test_invalid_kind(client, auth_headers):
    r = client.post(f"{PREFIX}/alerts", json=_alert(kind="moon"), headers=auth_headers)
    assert r.status_code == 400


def test_price_alert_invalid_coin_id(client, auth_headers):
    r = client.post(f"{PREFIX}/alerts", json=_alert(coin="Bad Id!"), headers=auth_headers)
    assert r.status_code == 400


def test_delete_unknown_404(client, auth_headers):
    assert client.delete(f"{PREFIX}/alerts/9999", headers=auth_headers).status_code == 404


def test_per_user_isolation(client, auth_headers, other_headers):
    aid = client.post(f"{PREFIX}/alerts", json=_alert(), headers=auth_headers).json()["id"]
    assert client.get(f"{PREFIX}/alerts", headers=other_headers).json() == []
    # other kann fremden Alert nicht löschen
    assert client.delete(f"{PREFIX}/alerts/{aid}", headers=other_headers).status_code == 404
    assert len(client.get(f"{PREFIX}/alerts", headers=auth_headers).json()) == 1


# ---------------------------------------------------------------- Poller
@pytest.fixture
def mock_price(monkeypatch):
    state = {"price": 90000.0, "change": 1.0}

    async def fake_markets(vs, *, ids=None, top=None):
        return [{"id": "bitcoin", "price": state["price"], "change_24h": state["change"]}]

    monkeypatch.setattr(cg, "markets", fake_markets)
    return state


@pytest.mark.asyncio
async def test_poller_feuert_bei_uebertritt(client, auth_headers, mock_price):
    client.post(f"{PREFIX}/alerts", json=_alert(threshold=100000.0), headers=auth_headers)

    # 1. Lauf: 90000 < 100000 → kein Feuern (etabliert last_value)
    mock_price["price"] = 90000.0
    await alert_poller.poll()
    ev = client.get(f"{PREFIX}/alerts/events", headers=auth_headers).json()
    assert ev["unseen"] == 0

    # 2. Lauf: 110000 ≥ 100000, Übertritt → feuert
    mock_price["price"] = 110000.0
    await alert_poller.poll()
    ev = client.get(f"{PREFIX}/alerts/events", headers=auth_headers).json()
    assert ev["unseen"] == 1
    assert "BTC" in ev["events"][0]["message"]

    # 3. Lauf: weiter drüber (120000) → KEIN erneutes Feuern
    mock_price["price"] = 120000.0
    await alert_poller.poll()
    ev = client.get(f"{PREFIX}/alerts/events", headers=auth_headers).json()
    assert ev["unseen"] == 1


@pytest.mark.asyncio
async def test_inaktiver_alert_feuert_nicht(client, auth_headers, mock_price):
    aid = client.post(f"{PREFIX}/alerts", json=_alert(threshold=100000.0), headers=auth_headers).json()["id"]
    client.patch(f"{PREFIX}/alerts/{aid}", json={"active": False}, headers=auth_headers)
    mock_price["price"] = 90000.0
    await alert_poller.poll()
    mock_price["price"] = 110000.0
    await alert_poller.poll()
    assert client.get(f"{PREFIX}/alerts/events", headers=auth_headers).json()["unseen"] == 0


@pytest.mark.asyncio
async def test_mark_seen(client, auth_headers, mock_price):
    client.post(f"{PREFIX}/alerts", json=_alert(threshold=100000.0), headers=auth_headers)
    mock_price["price"] = 90000.0
    await alert_poller.poll()
    mock_price["price"] = 110000.0
    await alert_poller.poll()
    assert client.get(f"{PREFIX}/alerts/events", headers=auth_headers).json()["unseen"] == 1
    assert client.post(f"{PREFIX}/alerts/events/seen", headers=auth_headers).status_code == 200
    assert client.get(f"{PREFIX}/alerts/events", headers=auth_headers).json()["unseen"] == 0
