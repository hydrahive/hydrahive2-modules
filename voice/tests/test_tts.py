"""Voice-Modul E7 — TTS-Auswahl (Bridge + media_models gemockt)."""
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
    routes: dict = {}
    last_post = None

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        return _FakeAsyncClient.routes["GET " + url.split("8898")[-1]]

    async def post(self, url, json=None):
        _FakeAsyncClient.last_post = json
        return _FakeAsyncClient.routes["POST " + url.split("8898")[-1]]


def _fake_httpx():
    import types
    m = types.SimpleNamespace()
    m.AsyncClient = _FakeAsyncClient
    return m


@pytest.fixture
def mock_tts(monkeypatch):
    import backend.tts as t
    monkeypatch.setattr(t, "httpx", _fake_httpx())
    _FakeAsyncClient.routes = {}
    _FakeAsyncClient.last_post = None

    async def fake_speech_models():
        return [
            {"id": "deepgram/aura-2", "voices": ["aura-2-julius-de", "aura-2-thalia-en"]},
            {"id": "minimax/speech-2.8-hd", "voices": []},
        ]

    monkeypatch.setattr(t.media_models, "list_speech_models", fake_speech_models)
    monkeypatch.setattr(t.media_models, "get_media_model", lambda cat: "deepgram/aura-2")
    return _FakeAsyncClient


# ── GET /tts ─────────────────────────────────────────────────────────────────
def test_tts_needs_auth(client):
    assert client.get(f"{PREFIX}/tts").status_code == 401


def test_tts_get_ok(client, user_headers, mock_tts):
    mock_tts.routes["GET /tts"] = _FakeResp(200, {"backend": "cloud", "model": "deepgram/aura-2", "voice": "aura-2-julius-de"})
    r = client.get(f"{PREFIX}/tts", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["bridge"] == "up"
    assert body["config"]["backend"] == "cloud"


def test_tts_get_bridge_down(client, user_headers, mock_tts):
    r = client.get(f"{PREFIX}/tts", headers=user_headers)  # keine Route → down
    assert r.status_code == 200
    assert r.json()["bridge"] == "down"
    assert r.json()["config"] is None


# ── PUT /tts ─────────────────────────────────────────────────────────────────
def test_tts_put_needs_auth(client):
    assert client.put(f"{PREFIX}/tts", json={"backend": "local"}).status_code == 401


def test_tts_put_backend_local(client, user_headers, mock_tts):
    mock_tts.routes["POST /tts"] = _FakeResp(200, {"backend": "local", "model": "", "voice": ""})
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={"backend": "local"})
    assert r.status_code == 200
    assert r.json()["config"]["backend"] == "local"
    assert mock_tts.last_post == {"backend": "local"}


def test_tts_put_cloud_with_model_voice(client, user_headers, mock_tts):
    mock_tts.routes["POST /tts"] = _FakeResp(200, {"backend": "cloud", "model": "deepgram/aura-2", "voice": "aura-2-julius-de"})
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={
        "backend": "cloud", "model": "deepgram/aura-2", "voice": "aura-2-julius-de",
    })
    assert r.status_code == 200
    assert mock_tts.last_post["model"] == "deepgram/aura-2"


def test_tts_put_invalid_backend_422(client, user_headers, mock_tts):
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={"backend": "telepathy"})
    assert r.status_code == 422
    assert mock_tts.last_post is None


def test_tts_put_unknown_model_422(client, user_headers, mock_tts):
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={"model": "evil/model"})
    assert r.status_code == 422
    assert mock_tts.last_post is None


def test_tts_put_empty_model_allowed(client, user_headers, mock_tts):
    # leeres Modell = zurück auf Default, keine Katalog-Prüfung
    mock_tts.routes["POST /tts"] = _FakeResp(200, {"backend": "cloud", "model": "", "voice": ""})
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={"model": ""})
    assert r.status_code == 200


def test_tts_put_no_fields_422(client, user_headers, mock_tts):
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={})
    assert r.status_code == 422


def test_tts_put_bridge_unreachable_503(client, user_headers, mock_tts):
    # gültiges backend, aber keine POST-Route → KeyError → 503
    r = client.put(f"{PREFIX}/tts", headers=user_headers, json={"backend": "local"})
    assert r.status_code == 503


# ── GET /tts/models ──────────────────────────────────────────────────────────
def test_tts_models_needs_auth(client):
    assert client.get(f"{PREFIX}/tts/models").status_code == 401


def test_tts_models_list(client, user_headers, mock_tts):
    r = client.get(f"{PREFIX}/tts/models", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["default"] == "deepgram/aura-2"
    ids = [m["id"] for m in body["models"]]
    assert "deepgram/aura-2" in ids
    aura = next(m for m in body["models"] if m["id"] == "deepgram/aura-2")
    assert "aura-2-julius-de" in aura["voices"]
