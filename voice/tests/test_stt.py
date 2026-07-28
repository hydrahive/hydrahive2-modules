"""Voice-Modul E6 — STT-Modell-Anzeige."""
from __future__ import annotations

import pytest

PREFIX = "/api/modules/voice"


# ── _parse_info (reine Funktion) ─────────────────────────────────────────────
def test_parse_info_prefers_installed():
    from backend.stt import _parse_info
    data = {
        "asr": [
            {
                "name": "faster-whisper",
                "models": [
                    {"name": "tiny", "installed": False, "languages": ["en"]},
                    {"name": "medium", "installed": True, "languages": ["de", "en", "fr"]},
                ],
            }
        ]
    }
    r = _parse_info(data)
    assert r["available"] is True
    assert r["program"] == "faster-whisper"
    assert r["model"] == "medium"
    assert r["languages"][:2] == ["de", "en"]


def test_parse_info_falls_back_to_first():
    from backend.stt import _parse_info
    data = {"asr": [{"name": "fw", "models": [{"name": "base", "languages": []}]}]}
    r = _parse_info(data)
    assert r["model"] == "base"


def test_parse_info_empty():
    from backend.stt import _parse_info
    assert _parse_info({})["available"] is False
    assert _parse_info({"asr": []})["available"] is False
    assert _parse_info({"asr": [{"name": "x", "models": []}]})["available"] is False


def test_parse_info_limits_languages():
    from backend.stt import _parse_info
    langs = [f"l{i}" for i in range(20)]
    data = {"asr": [{"name": "fw", "models": [{"name": "m", "installed": True, "languages": langs}]}]}
    r = _parse_info(data)
    assert len(r["languages"]) == 8


# ── GET /stt ─────────────────────────────────────────────────────────────────
def test_stt_needs_auth(client):
    assert client.get(f"{PREFIX}/stt").status_code == 401


def test_stt_ok(client, user_headers, monkeypatch):
    import backend.stt as m

    async def fake_read():
        return {"available": True, "program": "faster-whisper", "model": "medium", "languages": ["de", "en"]}

    monkeypatch.setattr(m, "read_stt_info", fake_read)
    r = client.get(f"{PREFIX}/stt", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["model"] == "medium"
    assert body["program"] == "faster-whisper"


def test_stt_unavailable(client, user_headers, monkeypatch):
    import backend.stt as m

    async def fake_read():
        return {"available": False, "program": None, "model": None, "languages": []}

    monkeypatch.setattr(m, "read_stt_info", fake_read)
    r = client.get(f"{PREFIX}/stt", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["available"] is False


@pytest.mark.asyncio
async def test_read_stt_info_connection_error(monkeypatch):
    """read_stt_info fängt einen Verbindungsfehler ab → available False."""
    import backend.stt as m

    async def boom(*a, **kw):
        raise ConnectionRefusedError()

    monkeypatch.setattr(m.asyncio, "open_connection", boom)
    r = await m.read_stt_info()
    assert r["available"] is False
    assert r["model"] is None
