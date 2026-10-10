"""C2: Agent-Werkzeug storyteller_restructure – Vorschlag oder direkt je Schalter, Helfer nur Vorschlag."""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import PROJECT_ID

from backend import restructure, storage
from backend.agent_tools import TOOLS


def _ctx(agent_id="agent-1", user="testuser", project_id=PROJECT_ID):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess-1", agent_id=agent_id, user_id=user, workspace=Path("/tmp"), project_id=project_id)


TOOL = next(t for t in TOOLS if t.name == "storyteller_restructure")


@pytest.fixture
def author(monkeypatch):
    """Projekt-Agent (Autor) ist agent-author; der Kern liefert ihn über projects.config.get."""
    from hydrahive.projects import config as pc
    real = pc.get
    monkeypatch.setattr(pc, "get", lambda pid: {**(real(pid) or {"id": pid}), "agent_id": "agent-author"}
                        if pid == PROJECT_ID else real(pid))
    return "agent-author"


def _book(mode=None):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    if mode:
        b = storage.update_book(PROJECT_ID, b["id"], {"ghost": {"agent_structure": mode}}, base_version=b["version"])
    st = storage.get_structure(PROJECT_ID, b["id"])
    return b["id"], st["parts"][0]["chapters"][0]["id"]


def _title(bid):
    return storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"][0]["title"]


STEP = lambda cid: [{"op": "rename_chapter", "chapter_id": cid, "title": "Neu"}]


async def test_default_is_proposal_even_for_the_author(author):
    bid, cid = _book()
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid), "note": "Titel"}, _ctx(author))
    assert res.success and res.output["mode"] == "proposal" and res.output["lines"] == ["Kapitel „Kapitel 1“ umbenennen in „Neu“"]
    assert _title(bid) == "Kapitel 1" and restructure.get(PROJECT_ID, bid)["note"] == "Titel"


async def test_author_changes_directly_when_switch_is_on(author):
    bid, cid = _book("direct")
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid) + [
        {"op": "add_chapter", "title": "K2", "scenes": [{"title": "S"}]}]}, _ctx(author))
    assert res.success and res.output["mode"] == "direct" and _title(bid) == "Neu"
    assert set(res.output["ids"]["chapters"]) == {"new:1"} and restructure.find(PROJECT_ID, bid) is None


async def test_helper_only_proposes_even_when_switch_is_on(author):
    bid, cid = _book("direct")
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid)}, _ctx("agent-helper"))
    assert res.success and res.output["mode"] == "proposal" and _title(bid) == "Kapitel 1"


async def test_errors_name_the_step_and_change_nothing(author):
    bid, cid = _book("direct")
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid) + [{"op": "delete_scene", "scene_id": "9" * 32}]},
                             _ctx(author))
    assert not res.success and "Schritt 2" in res.error and "delete_scene" in res.error and _title(bid) == "Kapitel 1"


async def test_last_chapter_error_is_readable(author):
    bid, cid = _book("direct")
    res = await TOOL.execute({"book_id": bid, "steps": [{"op": "delete_chapter", "chapter_id": cid}]}, _ctx(author))
    assert not res.success and "letzte Kapitel" in res.error


async def test_read_only_member_may_not_restructure(author):
    """reader hat im Projekt nur Leserecht – auch kein Vorschlag (wie alle Vorschlags-Werkzeuge)."""
    bid, cid = _book()
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid)}, _ctx(author, user="reader"))
    assert not res.success and "Leserecht" in res.error
    assert _title(bid) != "Neu"


async def test_without_agent_on_either_side_it_is_only_a_proposal(monkeypatch):
    """Projekt ohne agent_id und Aufruf ohne agent_id: kein „Autor“ → auch bei direct nur Vorschlag."""
    from hydrahive.projects import config as pc
    real = pc.get
    monkeypatch.setattr(pc, "get", lambda pid: {**(real(pid) or {"id": pid}), "agent_id": None}
                        if pid == PROJECT_ID else real(pid))
    bid, cid = _book("direct")
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid)}, _ctx(None))
    assert res.success and res.output["mode"] == "proposal"


async def test_reader_and_foreign_book_are_refused(author):
    bid, cid = _book()
    res = await TOOL.execute({"book_id": bid, "steps": STEP(cid)}, _ctx(author, user="nobody"))
    assert not res.success
    res = await TOOL.execute({"book_id": "f" * 32, "steps": STEP(cid)}, _ctx(author))
    assert not res.success and "Buch" in res.error


def test_tool_is_in_author_and_structure_role_and_team_version_bumped():
    from backend import team
    assert "storyteller_restructure" in team.AUTHOR.tools
    structure = next(r for r in team.HELPERS if r.key == "structure")
    assert "storyteller_restructure" in structure.tools
    assert all("storyteller_restructure" not in r.tools for r in team.HELPERS if r.key != "structure")
    assert team.TEAM_VERSION >= 3
    prompt = team.prompt_for(team.AUTHOR, book_title="B")
    assert "storyteller_restructure" in prompt and "new:1" in prompt
