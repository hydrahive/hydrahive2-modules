"""Schreib-Werkzeug idea_write: der Agent merkt an, ändert aber nie den Text des Nutzers."""
from __future__ import annotations

import pytest
from helpers import PROJECT_A, PROJECT_B, make_ctx


def _store():
    from backend import store
    return store


def _notes(idea_id: str, username: str = "alice") -> list[dict]:
    from backend import notes
    return notes.list_for(username, idea_id)


async def _write(args: dict, **ctx):
    from backend.tools_write import WRITE_TOOL
    return await WRITE_TOOL.execute(args, make_ctx(**ctx))


@pytest.fixture
def agent_name(monkeypatch):
    from backend import tools_write
    monkeypatch.setattr(tools_write, "agent_name", lambda ctx: "Buddy")


async def test_neue_idee_hat_herkunft_agent_und_das_aktive_projekt():
    result = await _write({"title": "Vorschlag", "body": "So könnte es gehen"}, project_id=PROJECT_A)
    assert result.success, result.error
    assert result.output["created"] is True
    idea = _store().get("alice", result.output["idea"]["id"])
    assert (idea["title"], idea["body"], idea["origin"], idea["project_id"]) == (
        "Vorschlag", "So könnte es gehen", "agent", PROJECT_A)


async def test_neue_idee_ohne_aktives_projekt_und_mit_none():
    ohne = await _write({"title": "Frei"})
    assert _store().get("alice", ohne.output["idea"]["id"])["project_id"] is None
    none = await _write({"title": "Bewusst frei", "project_id": "none"}, project_id=PROJECT_A)
    assert _store().get("alice", none.output["idea"]["id"])["project_id"] is None


async def test_neue_idee_braucht_titel_und_erlaubtes_projekt():
    for args in ({}, {"title": "  "}, {"body": "nur Text"}, {"title": "x" * 201}):
        assert not (await _write(args)).success
    fremd = await _write({"title": "Fremd", "project_id": PROJECT_B})
    assert not fremd.success and "Projekt" in fremd.error
    assert _store().count("alice") == 0


async def test_anmerkung_anhaengen(agent_name):
    idea = _store().create("alice", title="Meine Idee", body="mein Text")
    result = await _write({"idea_id": idea["id"][:8], "note": "  Erst das Datenmodell klären  "})
    assert result.success, result.error
    assert result.output["created"] is False
    notes = _notes(idea["id"])
    assert [(n["author"], n["agent_name"], n["body"]) for n in notes] == [
        ("agent", "Buddy", "Erst das Datenmodell klären")]
    unchanged = _store().get("alice", idea["id"])
    assert (unchanged["title"], unchanged["body"], unchanged["status"]) == ("Meine Idee", "mein Text", "new")


async def test_status_aendern_schreibt_anmerkung(agent_name):
    idea = _store().create("alice", title="Meine Idee")
    result = await _write({"idea_id": idea["id"], "status": "planned"})
    assert result.success, result.error
    assert _store().get("alice", idea["id"])["status"] == "planned"
    notes = _notes(idea["id"])
    assert [(n["author"], n["agent_name"], n["body"]) for n in notes] == [
        ("system", "Buddy", "Status: Neu → Geplant")]
    assert (await _write({"idea_id": idea["id"], "status": "planned"})).success
    assert len(_notes(idea["id"])) == 1


async def test_status_und_anmerkung_zusammen(agent_name):
    idea = _store().create("alice", title="Meine Idee")
    result = await _write({"idea_id": idea["id"], "status": "parked", "note": "Braucht erst Etappe 3"})
    assert result.success, result.error
    assert [n["body"] for n in _notes(idea["id"])] == ["Status: Neu → Geparkt", "Braucht erst Etappe 3"]


@pytest.mark.parametrize("change", [{"title": "Umbenannt"}, {"body": "Überschrieben"}, {"title": "A", "body": "B"}])
async def test_text_einer_nutzer_idee_ist_geschuetzt(change):
    idea = _store().create("alice", title="Meine Idee", body="mein Text")
    result = await _write({"idea_id": idea["id"], **change})
    assert not result.success
    assert "note" in result.error
    unchanged = _store().get("alice", idea["id"])
    assert (unchanged["title"], unchanged["body"]) == ("Meine Idee", "mein Text")
    assert _notes(idea["id"]) == []


async def test_geschuetzter_text_verhindert_auch_die_mitgeschickte_anmerkung():
    idea = _store().create("alice", title="Meine Idee", body="mein Text")
    result = await _write({"idea_id": idea["id"], "body": "Neu", "note": "und eine Anmerkung", "status": "done"})
    assert not result.success
    assert _notes(idea["id"]) == []
    assert _store().get("alice", idea["id"])["status"] == "new"


async def test_text_einer_agent_idee_darf_der_agent_aendern():
    idea = _store().create("alice", title="Entwurf", body="alt", origin="agent")
    result = await _write({"idea_id": idea["id"], "title": "Entwurf 2", "body": "neu"})
    assert result.success, result.error
    changed = _store().get("alice", idea["id"])
    assert (changed["title"], changed["body"], changed["origin"]) == ("Entwurf 2", "neu", "agent")


async def test_ungueltige_eingaben():
    idea = _store().create("alice", title="Meine Idee")
    assert not (await _write({"idea_id": idea["id"]})).success
    assert not (await _write({"idea_id": idea["id"], "status": "fertig"})).success
    assert not (await _write({"idea_id": idea["id"], "note": "x" * 10_001})).success
    assert not (await _write({"idea_id": idea["id"], "note": 42})).success
    assert not (await _write({"idea_id": "ffff0000", "note": "ins Leere"})).success
    assert not (await _write({"idea_id": idea["id"], "note": "fremd"}, username="bob")).success
    assert not (await _write({"title": "Ohne Nutzer"}, username="")).success
    assert _notes(idea["id"]) == []
    assert _store().get("alice", idea["id"])["status"] == "new"


async def test_projekt_einer_idee_aendert_das_werkzeug_nicht():
    idea = _store().create("alice", title="Meine Idee", project_id=PROJECT_A)
    result = await _write({"idea_id": idea["id"], "project_id": "none", "note": "Hinweis"})
    assert result.success, result.error
    assert _store().get("alice", idea["id"])["project_id"] == PROJECT_A


async def test_obergrenze_meldet_klartext(monkeypatch):
    s = _store()
    monkeypatch.setattr(s, "MAX_IDEAS", 1)
    s.create("alice", title="Voll")
    result = await _write({"title": "Zu viel"})
    assert not result.success and "2000" not in result.error and "Ideen" in result.error


def test_agentenname_aus_der_konfiguration(monkeypatch):
    from backend import tools_write
    from hydrahive.agents import config as agent_config

    monkeypatch.setattr(agent_config, "get", lambda agent_id: {"id": agent_id, "name": "Projekt-Agent"})
    assert tools_write.agent_name(make_ctx()) == "Projekt-Agent"
    monkeypatch.setattr(agent_config, "get", lambda agent_id: None)
    assert tools_write.agent_name(make_ctx()) is None
