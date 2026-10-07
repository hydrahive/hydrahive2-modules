"""Ghostwriter G4a: Agent-Werkzeuge – Zugriff (nur Sitzungsprojekt, Rolle) und Lesen (Spec §11.1)."""
from __future__ import annotations

import json
from pathlib import Path

from conftest import OTHER_PROJECT_ID, PROJECT_ID

from backend import interviews, proposals, storage
from backend.agent_tools import TOOLS, read


def _ctx(project_id=PROJECT_ID, user="testuser"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess-1", agent_id="agent-1", user_id=user, workspace=Path("/tmp"), project_id=project_id)


def _book(title="Der Leuchtturm"):
    b = storage.create_book(PROJECT_ID, {"title": title, "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]
    s1 = ch["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], s1, {"summary": "Mia kommt an.", "text": "Mia stand am Kai. " * 3}, base_version=1)
    s2 = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "Nacht", after=s1)["scene"]["id"]
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": "e" * 32, "kind": "character", "name": "Mia", "aliases": [], "description": "Zwölf.", "fields": []}]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    return b["id"], ch["id"], s1, s2


def _tool(name):
    return next(t for t in TOOLS if t.name == name)


async def test_no_project_in_session_gives_clear_message():
    res = await _tool("storyteller_books").execute({}, _ctx(project_id=None))
    assert not res.success and "keinem Projekt" in res.error and "Kein Zugriff" not in res.error


async def test_non_member_gets_no_access_and_no_details():
    _book()
    res = await _tool("storyteller_books").execute({}, _ctx(user="other"))
    assert not res.success and "Kein Zugriff" in res.error and PROJECT_ID not in json.dumps(res.output or {})


async def test_project_id_argument_is_ignored_only_session_project_counts():
    bid, *_ = _book()
    res = await _tool("storyteller_outline").execute({"book_id": bid, "project_id": OTHER_PROJECT_ID}, _ctx())
    assert res.success and res.output["book"]["id"] == bid
    schema_props = _tool("storyteller_outline").schema["properties"]
    assert "project_id" not in schema_props


async def test_books_lists_with_words():
    bid, *_ = _book()
    res = await _tool("storyteller_books").execute({}, _ctx(user="reader"))
    assert res.success
    b = next(x for x in res.output["books"] if x["id"] == bid)
    assert b["title"] == "Der Leuchtturm" and b["kind"] == "novel" and b["words"] == 12


async def test_outline_structure_entities_origin_and_proposal_flag():
    bid, cid, s1, s2 = _book()
    proposals.store(PROJECT_ID, bid, s2, "Vorschlag", run_id="r", model="m", base_version=1)
    res = await _tool("storyteller_outline").execute({"book_id": bid}, _ctx())
    assert res.success
    o = res.output
    scenes = [s for p in o["parts"] for c in p["chapters"] for s in c["scenes"]]
    assert [s["id"] for s in scenes] == [s1, s2]
    assert scenes[0] == {"id": s1, "title": scenes[0]["title"], "summary": "Mia kommt an.", "pov": "", "status": scenes[0]["status"],
                         "origin": "human", "words": 12, "has_proposal": False}
    assert scenes[1]["has_proposal"] is True
    assert o["entities"][0]["name"] == "Mia" and o["entities"][0]["description"] == "Zwölf."
    dumped = json.dumps(o)                          # muss serialisierbar sein
    assert "storyteller/books" not in dumped and "/var/" not in dumped and "workspace" not in dumped   # keine Pfade


async def test_outline_unknown_book_is_clear():
    res = await _tool("storyteller_outline").execute({"book_id": "f" * 32}, _ctx())
    assert not res.success and "Buch" in res.error


async def test_read_scenes_with_limit_and_cut_hint(monkeypatch):
    bid, cid, s1, s2 = _book()
    monkeypatch.setattr(read, "MAX_TEXT", 20)
    res = await _tool("storyteller_read").execute({"book_id": bid, "scene_ids": [s1, s2]}, _ctx(user="reader"))
    assert res.success
    a, b = res.output["scenes"]
    assert a["id"] == s1 and len(a["text"]) == 20 and a["cut"] is True and a["words"] == 12 and a["version"] == 2
    assert b["id"] == s2 and b["text"] == "" and b["cut"] is False


async def test_read_limits_number_and_unknown_scene():
    bid, cid, s1, s2 = _book()
    many = await _tool("storyteller_read").execute({"book_id": bid, "scene_ids": [s1] * 4}, _ctx())
    assert not many.success and "3" in many.error
    unknown = await _tool("storyteller_read").execute({"book_id": bid, "scene_ids": ["a" * 32]}, _ctx())
    assert not unknown.success and "Szene" in unknown.error
    empty = await _tool("storyteller_read").execute({"book_id": bid, "scene_ids": []}, _ctx())
    assert not empty.success


async def test_read_interview_of_chapter():
    bid, cid, *_ = _book()
    interviews.save(PROJECT_ID, bid, cid, [{"id": "a" * 32, "question": "Wann?", "answer": "1987."}], base_version=0)
    res = await _tool("storyteller_read").execute({"book_id": bid, "interview_chapter_id": cid}, _ctx())
    assert res.success and res.output["interview"]["questions"][0]["answer"] == "1987."


def test_tools_have_unique_names_schemas_and_hints():
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names)) and all(n.startswith("storyteller_") for n in names)
    for t in TOOLS:
        assert t.schema["type"] == "object" and t.description
    assert any("nie" in (t.prompt_hint or "").lower() for t in TOOLS)
