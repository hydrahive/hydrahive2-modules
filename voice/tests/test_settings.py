"""Voice-Modul E2 — Status + Settings (Bridge gemockt)."""
from __future__ import annotations

import pytest

PREFIX = "/api/modules/voice"


class _FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _FakeAsyncClient:
    """Ersetzt httpx.AsyncClient — routet GET/POST auf ein Handler-Dict."""

    routes: dict = {}

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        return _FakeAsyncClient.routes["GET " + url.split("8898")[-1]]

    async def post(self, url, json=None):
        _FakeAsyncClient.last_post = (url, json)
        return _FakeAsyncClient.routes["POST " + url.split("8898")[-1]]


@pytest.fixture
def mock_bridge(monkeypatch):
    import backend
    monkeypatch.setattr(backend, "httpx", _fake_httpx())
    _FakeAsyncClient.routes = {}
    _FakeAsyncClient.last_post = None
    return _FakeAsyncClient


def _fake_httpx():
    import types
    m = types.SimpleNamespace()
    m.AsyncClient = _FakeAsyncClient
    return m


def _state(**over):
    base = {
        "connected": True,
        "volume": 0.8,
        "mute": False,
        "wake_sound": True,
        "wake_word_sensitivity": "Very sensitive",
        "led_on": False,
        "led_brightness": 0.66,
    }
    base.update(over)
    return base


# ── /status ───────────────────────────────────────────────────────────────
def test_status_needs_auth(client):
    assert client.get(f"{PREFIX}/status").status_code == 401


def test_status_bridge_up(client, user_headers, mock_bridge):
    mock_bridge.routes["GET /health"] = _FakeResp(200, {"ok": True, "connected": True})
    r = client.get(f"{PREFIX}/status", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "e2"
    assert body["bridge"] == "up"
    assert body["device"] == "connected"


def test_status_bridge_down(client, user_headers, mock_bridge):
    # keine Route registriert → get wirft KeyError → _bridge_get gibt None
    r = client.get(f"{PREFIX}/status", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["bridge"] == "down"


# ── GET /settings ──────────────────────────────────────────────────────────
def test_get_settings_needs_auth(client):
    assert client.get(f"{PREFIX}/settings").status_code == 401


def test_get_settings_ok(client, user_headers, mock_bridge):
    mock_bridge.routes["GET /state"] = _FakeResp(200, _state())
    r = client.get(f"{PREFIX}/settings", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["bridge"] == "up"
    assert body["settings"]["volume"] == 0.8
    assert body["settings"]["wake_word_sensitivity"] == "Very sensitive"


def test_get_settings_bridge_down(client, user_headers, mock_bridge):
    r = client.get(f"{PREFIX}/settings", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["bridge"] == "down"
    assert r.json()["settings"] is None


# ── PUT /settings ──────────────────────────────────────────────────────────
def test_put_settings_needs_auth(client):
    assert client.put(f"{PREFIX}/settings", json={"volume": 0.3}).status_code == 401


def test_put_settings_ok(client, user_headers, mock_bridge):
    mock_bridge.routes["POST /set"] = _FakeResp(200, _state(volume=0.3))
    r = client.put(f"{PREFIX}/settings", headers=user_headers, json={"volume": 0.3})
    assert r.status_code == 200
    assert r.json()["settings"]["volume"] == 0.3
    # Payload wurde an die Bridge geschickt
    _url, payload = mock_bridge.last_post
    assert payload == {"volume": 0.3}


def test_put_settings_invalid_volume_422_no_bridge_call(client, user_headers, mock_bridge):
    r = client.put(f"{PREFIX}/settings", headers=user_headers, json={"volume": 9})
    assert r.status_code == 422
    assert mock_bridge.last_post is None  # kein Geräte-Call


def test_put_settings_invalid_sensitivity_422(client, user_headers, mock_bridge):
    r = client.put(
        f"{PREFIX}/settings", headers=user_headers,
        json={"wake_word_sensitivity": "Nope"},
    )
    assert r.status_code == 422
    assert mock_bridge.last_post is None


def test_put_settings_empty_422(client, user_headers, mock_bridge):
    r = client.put(f"{PREFIX}/settings", headers=user_headers, json={"foo": 1})
    assert r.status_code == 422


def test_put_settings_device_disconnected_503(client, user_headers, mock_bridge):
    mock_bridge.routes["POST /set"] = _FakeResp(503, {"error": "device_disconnected"})
    r = client.put(f"{PREFIX}/settings", headers=user_headers, json={"volume": 0.3})
    assert r.status_code == 503


def test_put_settings_bridge_unreachable_503(client, user_headers, mock_bridge):
    # keine POST-Route → KeyError → except → 503 bridge_unreachable
    r = client.put(f"{PREFIX}/settings", headers=user_headers, json={"volume": 0.3})
    assert r.status_code == 503
