"""Routen-Tests — Auth, Proxy-Verhalten (client gemockt), Favoriten-Ownership."""
from __future__ import annotations

import pytest

from backend import client as ha_client


@pytest.fixture
def mock_ha(monkeypatch):
    """HA-Client mit Beispieldaten mocken — kein echter Traffic."""
    states = [
        {"entity_id": "light.wohnzimmer", "state": "on", "name": "Wohnzimmer",
         "domain": "light", "unit": None, "attributes": {}},
    ]

    async def fake_ping():
        return {"ok": True, "message": "API running."}

    async def fake_config():
        return {"location_name": "Zuhause", "version": "2026.6.0"}

    async def fake_states():
        return states

    async def fake_state(eid):
        return states[0]

    async def fake_call(domain, service, data):
        return states

    monkeypatch.setattr(ha_client, "ping", fake_ping)
    monkeypatch.setattr(ha_client, "config", fake_config)
    monkeypatch.setattr(ha_client, "states", fake_states)
    monkeypatch.setattr(ha_client, "state", fake_state)
    monkeypatch.setattr(ha_client, "call_service", fake_call)


# ---- Auth ----
def test_states_requires_auth(client):
    assert client.get("/api/modules/homeassistant/states").status_code in (401, 403)


def test_service_requires_auth(client):
    r = client.post("/api/modules/homeassistant/service",
                    json={"domain": "light", "service": "turn_on"})
    assert r.status_code in (401, 403)


# ---- Proxy ----
def test_test_endpoint(client, auth_headers, mock_ha):
    r = client.get("/api/modules/homeassistant/test", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["config"]["location_name"] == "Zuhause"


def test_states(client, auth_headers, mock_ha):
    r = client.get("/api/modules/homeassistant/states", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()[0]["entity_id"] == "light.wohnzimmer"


def test_state_invalid_id(client, auth_headers, mock_ha):
    r = client.get("/api/modules/homeassistant/states/kaputt", headers=auth_headers)
    assert r.status_code == 400


def test_service_call(client, auth_headers, mock_ha):
    r = client.post("/api/modules/homeassistant/service",
                    json={"domain": "light", "service": "turn_on", "entity_id": "light.wohnzimmer"},
                    headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["changed"]) == 1


def test_service_domain_mismatch(client, auth_headers, mock_ha):
    r = client.post("/api/modules/homeassistant/service",
                    json={"domain": "switch", "service": "turn_on", "entity_id": "light.wohnzimmer"},
                    headers=auth_headers)
    assert r.status_code == 400


def test_not_configured_returns_503(client, auth_headers, monkeypatch):
    async def boom():
        raise ha_client.HAConfigError("URL fehlt")
    monkeypatch.setattr(ha_client, "ping", boom)
    r = client.get("/api/modules/homeassistant/test", headers=auth_headers)
    assert r.status_code == 503


def test_upstream_error_returns_502(client, auth_headers, monkeypatch):
    async def boom():
        raise ha_client.HAError("Token abgelehnt")
    monkeypatch.setattr(ha_client, "states", boom)
    r = client.get("/api/modules/homeassistant/states", headers=auth_headers)
    assert r.status_code == 502


# ---- Favoriten ----
def test_favorites_crud(client, auth_headers):
    base = "/api/modules/homeassistant/favorites"
    assert client.get(base, headers=auth_headers).json() == []

    r = client.post(base, json={"entity_id": "light.wohnzimmer"}, headers=auth_headers)
    assert r.status_code == 200

    favs = client.get(base, headers=auth_headers).json()
    assert len(favs) == 1
    assert favs[0]["entity_id"] == "light.wohnzimmer"

    r = client.delete(f"{base}/light.wohnzimmer", headers=auth_headers)
    assert r.json()["removed"] is True
    assert client.get(base, headers=auth_headers).json() == []


def test_favorite_invalid_id(client, auth_headers):
    r = client.post("/api/modules/homeassistant/favorites",
                    json={"entity_id": "kaputt"}, headers=auth_headers)
    assert r.status_code == 400


def test_favorites_isolated_per_user(client):
    base = "/api/modules/homeassistant/favorites"
    h1 = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'username': 'testuser', 'password': 'testpass123'}).json()['access_token']}"}
    h2 = {"Authorization": f"Bearer {client.post('/api/auth/login', json={'username': 'other', 'password': 'testpass123'}).json()['access_token']}"}

    client.post(base, json={"entity_id": "light.wohnzimmer"}, headers=h1)
    assert len(client.get(base, headers=h1).json()) == 1
    assert client.get(base, headers=h2).json() == []
