"""Ghostwriter G4a: Chat mit dem Projekt-Agenten aus dem Storyteller starten (Spec §11.3)."""
from __future__ import annotations

import json

import pytest
from backend import storage
from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


@pytest.fixture
def project_agent(setup_test_env):
    """Projekt-Agent anlegen und im Projekt eintragen (wie der Kern beim Anlegen eines Projekts)."""
    from hydrahive.agents import config as agent_config
    a = agent_config.create(agent_type="project", name="Projekt-Agent Story", llm_model="claude-sonnet-4-6",
                            owner="testuser", created_by="testuser", tools=["file_read", "storyteller_books"],
                            temperature=0.7, max_tokens=4096, thinking_budget=0, project_id=PROJECT_ID)
    cfg = setup_test_env / "data" / "projects" / PROJECT_ID / "config.json"
    raw = json.loads(cfg.read_text())
    old = raw.get("agent_id")
    raw["agent_id"] = a["id"]
    cfg.write_text(json.dumps(raw))
    yield a
    raw["agent_id"] = old
    cfg.write_text(json.dumps(raw))
    agent_config.delete(a["id"])


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "Der Leuchtturm", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    return b["id"], sid


def test_chat_info_lists_agent_and_missing_tools(client, auth_headers, reader_headers, project_agent):
    bid, _ = _book()
    r = client.get(f"{P}/books/{bid}/chat", headers=reader_headers)
    assert r.status_code == 200
    info = r.json()
    assert info["agent"] == {"id": project_agent["id"], "name": "Projekt-Agent Story"}
    assert info["tools_missing"] == ["storyteller_outline", "storyteller_read", "storyteller_propose_text",
                                     "storyteller_propose_scene_info", "storyteller_propose_entity",
                                     "storyteller_propose_outline", "storyteller_restructure", "storyteller_note",
                                     "storyteller_notes"]
    assert info["can_start"] is False                          # Leser


def test_chat_start_creates_session_in_project_with_project_agent(client, auth_headers, project_agent):
    bid, sid = _book()
    r = client.post(f"{P}/books/{bid}/chat", json={"scene_id": sid}, headers=auth_headers)
    assert r.status_code == 200, r.text
    out = r.json()
    from hydrahive.db import sessions as sessions_db
    s = sessions_db.get(out["session_id"])
    assert s.agent_id == project_agent["id"] and s.project_id == PROJECT_ID and s.user_id == "testuser"
    assert s.title == "Storyteller: Der Leuchtturm"
    assert bid in out["intro"] and sid in out["intro"] and "storyteller_outline" in out["intro"]
    assert out["url"] == f"/werkstatt/{out['session_id']}"


def test_reader_cannot_start_and_foreign_project(client, reader_headers, other_headers, auth_headers, project_agent):
    bid, sid = _book()
    assert client.post(f"{P}/books/{bid}/chat", json={"scene_id": sid}, headers=reader_headers).status_code == 403
    assert client.post(f"{P}/books/{bid}/chat", json={}, headers=other_headers).status_code == 404
    other = f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books/{bid}/chat"
    assert client.post(other, json={}, headers=auth_headers).status_code == 404


def test_unknown_scene_and_book(client, auth_headers, project_agent):
    bid, _ = _book()
    assert client.post(f"{P}/books/{bid}/chat", json={"scene_id": "f" * 32}, headers=auth_headers).status_code == 404
    assert client.post(f"{P}/books/{'f' * 32}/chat", json={}, headers=auth_headers).status_code == 404
    assert client.get(f"{P}/books/{'f' * 32}/chat", headers=auth_headers).status_code == 404
    assert client.get(f"{P}/books/{'f' * 32}/proposals", headers=auth_headers).status_code == 404


def test_project_without_agent_is_clear(client, auth_headers, setup_test_env):
    bid, _ = _book()
    cfg = setup_test_env / "data" / "projects" / PROJECT_ID / "config.json"
    raw = json.loads(cfg.read_text())
    old = raw.pop("agent_id", None)
    cfg.write_text(json.dumps(raw))
    try:
        r = client.post(f"{P}/books/{bid}/chat", json={}, headers=auth_headers)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "project_agent_missing"
        assert client.get(f"{P}/books/{bid}/chat", headers=auth_headers).json()["agent"] is None
    finally:
        if old:
            raw["agent_id"] = old
        cfg.write_text(json.dumps(raw))


def test_proposals_list_route_for_polling(client, auth_headers, project_agent):
    """Oberfläche fragt offene Vorschläge nach (Agent hat im Chat einen abgelegt)."""
    from backend import proposals
    bid, sid = _book()
    proposals.store(PROJECT_ID, bid, sid, "Vom Agenten.", run_id="", model="", base_version=1, source="agent", session_id="s1")
    r = client.get(f"{P}/books/{bid}/proposals", headers=auth_headers)
    assert r.status_code == 200 and r.json()[0]["scene_id"] == sid and r.json()[0]["source"] == "agent"


def test_foreign_user_sees_neither_chat_info_nor_proposals(client, other_headers, project_agent):
    bid, _ = _book()
    assert client.get(f"{P}/books/{bid}/chat", headers=other_headers).status_code == 404
    assert client.get(f"{P}/books/{bid}/proposals", headers=other_headers).status_code == 404
    assert client.get(f"{P}/books/{'f' * 32}/proposals", headers=other_headers).status_code == 404


def test_new_session_is_marked_with_book_and_reuse_returns_it(client, auth_headers, project_agent):
    """G4e: Chat-Fenster im Storyteller nutzt je Buch dieselbe Sitzung (Verlauf bleibt)."""
    from hydrahive.db import sessions as sessions_db
    bid, sid = _book()
    first = client.post(f"{P}/books/{bid}/chat", json={"scene_id": sid}, headers=auth_headers).json()
    assert first["reused"] is False
    assert sessions_db.get(first["session_id"]).metadata.get("storyteller_book") == bid
    again = client.post(f"{P}/books/{bid}/chat", json={"reuse": True}, headers=auth_headers).json()
    assert again["reused"] is True and again["session_id"] == first["session_id"]
    fresh = client.post(f"{P}/books/{bid}/chat", json={}, headers=auth_headers).json()     # ohne reuse: neu
    assert fresh["session_id"] != first["session_id"] and fresh["reused"] is False
    newest = client.post(f"{P}/books/{bid}/chat", json={"reuse": True}, headers=auth_headers).json()
    assert newest["session_id"] == fresh["session_id"]                                       # jüngste gewinnt


def test_reuse_only_own_session_same_book_agent_and_project(client, auth_headers, project_agent):
    from hydrahive.db import sessions as sessions_db
    bid, _ = _book()
    other_bid, _ = _book()
    # fremde, falsche oder unmarkierte Sitzungen dürfen nicht gewählt werden
    sessions_db.create(agent_id=project_agent["id"], user_id="other", project_id=PROJECT_ID, metadata={"storyteller_book": bid})
    sessions_db.create(agent_id=project_agent["id"], user_id="testuser", project_id=PROJECT_ID, metadata={"storyteller_book": other_bid})
    sessions_db.create(agent_id="anderer-agent", user_id="testuser", project_id=PROJECT_ID, metadata={"storyteller_book": bid})
    sessions_db.create(agent_id=project_agent["id"], user_id="testuser", project_id=OTHER_PROJECT_ID, metadata={"storyteller_book": bid})
    sessions_db.create(agent_id=project_agent["id"], user_id="testuser", project_id=PROJECT_ID)
    r = client.post(f"{P}/books/{bid}/chat", json={"reuse": True}, headers=auth_headers).json()
    assert r["reused"] is False
    s = sessions_db.get(r["session_id"])
    assert s.user_id == "testuser" and s.agent_id == project_agent["id"] and s.project_id == PROJECT_ID
    assert s.metadata["storyteller_book"] == bid


def test_reuse_respects_reader_rights(client, reader_headers, project_agent):
    bid, _ = _book()
    assert client.post(f"{P}/books/{bid}/chat", json={"reuse": True}, headers=reader_headers).status_code == 403


def test_reuse_moves_the_session_to_the_front(client, auth_headers, project_agent):
    """Fund 07.10.: Die Kern-Chatansicht lädt nur die neuesten Sitzungen – die wiederverwendete muss vorn stehen."""
    import time

    from hydrahive.db import sessions as sessions_db
    bid, _ = _book()
    story = client.post(f"{P}/books/{bid}/chat", json={}, headers=auth_headers).json()["session_id"]
    time.sleep(0.01)
    newer = sessions_db.create(agent_id=project_agent["id"], user_id="testuser", project_id=PROJECT_ID, title="Anderer Chat")
    assert sessions_db.list_for_user("testuser")[0].id == newer.id
    r = client.post(f"{P}/books/{bid}/chat", json={"reuse": True}, headers=auth_headers).json()
    assert r["session_id"] == story and sessions_db.list_for_user("testuser")[0].id == story


def test_book_session_is_marked_embedded_for_the_cockpit(client, auth_headers, project_agent):
    """Task 8fd82c02: Kern-Cockpit öffnet Sitzungen mit metadata.embedded_in nie von selbst."""
    from hydrahive.db import sessions as sessions_db
    bid, _ = _book()
    r = client.post(f"{P}/books/{bid}/chat", json={}, headers=auth_headers).json()
    assert sessions_db.get(r["session_id"]).metadata.get("embedded_in") == "storyteller"


def test_reused_old_session_gets_marked_and_keeps_other_metadata(client, auth_headers, project_agent):
    """Sitzungen von vor 0.10.2 (nur storyteller_book) werden beim Wiederverwenden nachgezogen."""
    from hydrahive.db import sessions as sessions_db
    bid, _ = _book()
    old = sessions_db.create(agent_id=project_agent["id"], user_id="testuser", project_id=PROJECT_ID,
                             metadata={"storyteller_book": bid, "model_override": "irgendein-modell"})
    r = client.post(f"{P}/books/{bid}/chat", json={"reuse": True}, headers=auth_headers).json()
    assert r["reused"] is True and r["session_id"] == old.id
    md = sessions_db.get(old.id).metadata
    assert md == {"storyteller_book": bid, "model_override": "irgendein-modell", "embedded_in": "storyteller"}
