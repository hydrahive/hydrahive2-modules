"""C3 — Watchlist: CRUD + strikte per-User-Isolation."""
from __future__ import annotations

import pytest

PREFIX = "/api/modules/cryptoboard"


@pytest.fixture
def other_headers(client):
    r = client.post("/api/auth/login", json={"username": "other", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_watchlist_braucht_auth(client):
    assert client.get(f"{PREFIX}/watchlist").status_code == 401


def test_add_list_remove(client, auth_headers):
    assert client.get(f"{PREFIX}/watchlist", headers=auth_headers).json() == []

    r = client.post(f"{PREFIX}/watchlist", json={"coin_id": "bitcoin", "symbol": "btc", "name": "Bitcoin"}, headers=auth_headers)
    assert r.status_code == 200

    items = client.get(f"{PREFIX}/watchlist", headers=auth_headers).json()
    assert len(items) == 1
    assert items[0]["coin_id"] == "bitcoin"
    assert items[0]["symbol"] == "BTC"  # upper-cased

    r = client.delete(f"{PREFIX}/watchlist/bitcoin", headers=auth_headers)
    assert r.status_code == 200
    assert client.get(f"{PREFIX}/watchlist", headers=auth_headers).json() == []


def test_add_idempotent(client, auth_headers):
    for _ in range(2):
        client.post(f"{PREFIX}/watchlist", json={"coin_id": "bitcoin"}, headers=auth_headers)
    assert len(client.get(f"{PREFIX}/watchlist", headers=auth_headers).json()) == 1


def test_invalid_coin_id_400(client, auth_headers):
    r = client.post(f"{PREFIX}/watchlist", json={"coin_id": "Invalid Id!"}, headers=auth_headers)
    assert r.status_code == 400


def test_per_user_isolation(client, auth_headers, other_headers):
    client.post(f"{PREFIX}/watchlist", json={"coin_id": "bitcoin"}, headers=auth_headers)

    # other sieht testusers Watchlist NICHT
    assert client.get(f"{PREFIX}/watchlist", headers=other_headers).json() == []

    # other kann testusers Eintrag nicht löschen (löscht nur eigene → testuser bleibt)
    client.delete(f"{PREFIX}/watchlist/bitcoin", headers=other_headers)
    assert len(client.get(f"{PREFIX}/watchlist", headers=auth_headers).json()) == 1
