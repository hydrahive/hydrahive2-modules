"""Zugriffsschutz für die eine lokale Voicebox."""
from __future__ import annotations

import types
from typing import ClassVar

import pytest

PREFIX = "/api/modules/voice"


class _Response:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class _BridgeClient:
    routes: ClassVar[dict] = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params=None):
        return self.routes["GET " + url.split("8898")[-1]]

    async def post(self, url, json=None):
        return self.routes["POST " + url.split("8898")[-1]]


@pytest.fixture
def successful_bridge(monkeypatch):
    import backend
    from backend import tts

    fake_httpx = types.SimpleNamespace(AsyncClient=_BridgeClient)
    monkeypatch.setattr(backend, "httpx", fake_httpx)
    monkeypatch.setattr(tts, "httpx", fake_httpx)
    state = {
        "connected": True,
        "volume": 0.3,
        "mute": False,
        "wake_sound": True,
        "wake_word_sensitivity": "Very sensitive",
        "led_on": True,
        "led_brightness": 0.5,
    }
    _BridgeClient.routes = {
        "GET /health": _Response({"connected": True}),
        "GET /state": _Response(state),
        "POST /set": _Response(state),
        "GET /transcript": _Response({"turns": [], "cursor": 0}),
        "POST /say": _Response({"accepted": True}),
        "POST /tts": _Response({"backend": "local", "model": "", "voice": ""}),
    }
    return _BridgeClient


PROTECTED_ROUTES = (
    ("GET", "/settings", None),
    ("PUT", "/settings", {"volume": 0.3}),
    ("GET", "/transcript", None),
    ("POST", "/say", {"text": "hi"}),
    ("PUT", "/tts", {"backend": "local"}),
)


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED_ROUTES)
def test_foreign_user_is_forbidden_from_box_routes(
    client, foreign_headers, successful_bridge, method, path, body,
):
    response = client.request(
        method, f"{PREFIX}{path}", headers=foreign_headers, json=body,
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "voice_owner_required"


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED_ROUTES)
def test_admin_can_use_box_routes(
    client, admin_headers, successful_bridge, method, path, body,
):
    response = client.request(
        method, f"{PREFIX}{path}", headers=admin_headers, json=body,
    )
    assert response.status_code == 200


def test_owner_from_environment_can_use_box_route(
    client, user_headers, successful_bridge, monkeypatch,
):
    monkeypatch.setenv("VOICE_BRIDGE_OWNER", "user")
    response = client.get(f"{PREFIX}/transcript", headers=user_headers)
    assert response.status_code == 200


def test_non_admin_is_forbidden_without_known_owner(
    client, user_headers, successful_bridge, monkeypatch,
):
    monkeypatch.delenv("VOICE_BRIDGE_OWNER", raising=False)
    response = client.get(f"{PREFIX}/settings", headers=user_headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "voice_owner_required"


def test_owner_from_bridge_health_can_use_box_route(
    client, user_headers, successful_bridge, monkeypatch,
):
    monkeypatch.delenv("VOICE_BRIDGE_OWNER", raising=False)
    successful_bridge.routes["GET /health"] = _Response(
        {"connected": True, "owner": "user"},
    )
    response = client.get(f"{PREFIX}/settings", headers=user_headers)
    assert response.status_code == 200


def test_status_hides_device_details_from_foreign_user(
    client, foreign_headers, successful_bridge,
):
    response = client.get(f"{PREFIX}/status", headers=foreign_headers)
    assert response.status_code == 200
    assert response.json() == {"module": "voice", "stage": "e2"}
