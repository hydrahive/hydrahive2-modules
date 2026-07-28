"""Voice-Modul E5 — LLM-Auswahl (Master/Session/Registry gemockt)."""
from __future__ import annotations

import pytest

PREFIX = "/api/modules/voice"


class _ModelEntry:
    def __init__(self, id, label="L", provider="p"):
        self.id = id
        self.label = label
        self.provider = provider


class _Session:
    def __init__(self, metadata):
        self.metadata = metadata


@pytest.fixture
def mock_llm(monkeypatch):
    """Patcht die Core-Abhängigkeiten des llm-Backends."""
    import backend.llm as m

    state = {
        "master": {"id": "agent-1", "type": "master", "status": "active", "llm_model": "anthropic/claude-x"},
        "session_id": "sess-voice-1",
        "override": None,
        "models": ["anthropic/claude-x", "openai/gpt-mini", "meta/llama"],
        "set_calls": [],
    }

    def fake_find_master(username):
        return state["master"]

    def fake_voice_sid(agent_id):
        return state["session_id"]

    def fake_get(sid):
        if sid == state["session_id"]:
            return _Session({"model_override": state["override"]} if state["override"] else {})
        return None

    def fake_set_override(sid, model):
        state["set_calls"].append((sid, model))
        state["override"] = model

    async def fake_list_models(modality=None):
        return [_ModelEntry(i) for i in state["models"]]

    monkeypatch.setattr(m, "_find_master", fake_find_master)
    monkeypatch.setattr(m, "_voice_session_id", fake_voice_sid)
    monkeypatch.setattr(m.sessions_db, "get", fake_get)
    monkeypatch.setattr(m.sessions_db, "set_model_override", fake_set_override)
    monkeypatch.setattr(m.registry, "list_models", fake_list_models)
    return state


# ── GET /llm ────────────────────────────────────────────────────────────────
def test_llm_needs_auth(client):
    assert client.get(f"{PREFIX}/llm").status_code == 401


def test_llm_get_no_override(client, user_headers, mock_llm):
    r = client.get(f"{PREFIX}/llm", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["override"] is None
    assert body["agent_default"] == "anthropic/claude-x"
    assert body["has_session"] is True


def test_llm_get_with_override(client, user_headers, mock_llm):
    mock_llm["override"] = "openai/gpt-mini"
    r = client.get(f"{PREFIX}/llm", headers=user_headers)
    assert r.json()["override"] == "openai/gpt-mini"


def test_llm_get_no_master_404(client, user_headers, mock_llm, monkeypatch):
    import backend.llm as m
    monkeypatch.setattr(m, "_find_master", lambda u: None)
    r = client.get(f"{PREFIX}/llm", headers=user_headers)
    assert r.status_code == 404


def test_llm_get_no_session(client, user_headers, mock_llm):
    mock_llm["session_id"] = None
    r = client.get(f"{PREFIX}/llm", headers=user_headers)
    body = r.json()
    assert body["has_session"] is False
    assert body["override"] is None


# ── PUT /llm ────────────────────────────────────────────────────────────────
def test_llm_put_needs_auth(client):
    assert client.put(f"{PREFIX}/llm", json={"model": "x"}).status_code == 401


def test_llm_put_sets_override(client, user_headers, mock_llm):
    r = client.put(f"{PREFIX}/llm", headers=user_headers, json={"model": "openai/gpt-mini"})
    assert r.status_code == 200
    assert r.json()["override"] == "openai/gpt-mini"
    assert mock_llm["set_calls"][-1] == ("sess-voice-1", "openai/gpt-mini")


def test_llm_put_clears_override(client, user_headers, mock_llm):
    mock_llm["override"] = "openai/gpt-mini"
    r = client.put(f"{PREFIX}/llm", headers=user_headers, json={"model": ""})
    assert r.status_code == 200
    assert r.json()["override"] is None
    assert mock_llm["set_calls"][-1] == ("sess-voice-1", None)


def test_llm_put_null_clears(client, user_headers, mock_llm):
    r = client.put(f"{PREFIX}/llm", headers=user_headers, json={"model": None})
    assert r.status_code == 200
    assert mock_llm["set_calls"][-1] == ("sess-voice-1", None)


def test_llm_put_unknown_model_422(client, user_headers, mock_llm):
    r = client.put(f"{PREFIX}/llm", headers=user_headers, json={"model": "evil/model"})
    assert r.status_code == 422
    assert mock_llm["set_calls"] == []  # nichts gesetzt


def test_llm_put_no_session_409(client, user_headers, mock_llm):
    mock_llm["session_id"] = None
    r = client.put(f"{PREFIX}/llm", headers=user_headers, json={"model": "openai/gpt-mini"})
    assert r.status_code == 409


def test_llm_put_invalid_model_type_422(client, user_headers, mock_llm):
    r = client.put(f"{PREFIX}/llm", headers=user_headers, json={"model": 123})
    assert r.status_code == 422


# ── GET /llm/models ──────────────────────────────────────────────────────────
def test_llm_models_needs_auth(client):
    assert client.get(f"{PREFIX}/llm/models").status_code == 401


def test_llm_models_list(client, user_headers, mock_llm):
    r = client.get(f"{PREFIX}/llm/models", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["agent_default"] == "anthropic/claude-x"
    ids = [m["id"] for m in body["models"]]
    assert "openai/gpt-mini" in ids
    assert len(ids) == 3
