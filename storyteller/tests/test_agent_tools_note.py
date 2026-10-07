"""T1d: Werkzeuge storyteller_note / storyteller_notes + offene Hinweise in storyteller_outline."""
from __future__ import annotations

from pathlib import Path

from backend import storage, team_notes
from backend.agent_tools import TOOLS
from conftest import OTHER_PROJECT_ID, PROJECT_ID

NOTE = next(t for t in TOOLS if t.name == "storyteller_note")
NOTES = next(t for t in TOOLS if t.name == "storyteller_notes")
OUTLINE = next(t for t in TOOLS if t.name == "storyteller_outline")


def _ctx(user="testuser", project_id=PROJECT_ID, agent="agent-x"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess-9", agent_id=agent, user_id=user, workspace=Path("/tmp"), project_id=project_id)


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    return b["id"], storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]


async def test_note_stores_hint_with_origin_from_context(monkeypatch):
    from hydrahive.agents import config as agent_config
    monkeypatch.setattr(agent_config, "get", lambda aid: {"id": aid, "name": "Der Leuchtturm — Plausibilität"})
    bid, sid = _book()
    res = await NOTE.execute({"book_id": bid, "kind": "hint", "scene_id": sid, "title": "Augenfarbe",
                              "text": "blau vs. grün", "author": "gefälscht", "agent_id": "x"}, _ctx())
    assert res.success and res.output["stored"] is True and res.output["open_total"] == 1
    n = team_notes.list_notes(PROJECT_ID, bid)[0]
    assert n["author"] == "Der Leuchtturm — Plausibilität" and n["agent_id"] == "agent-x" and n["session_id"] == "sess-9"
    assert n["scene_id"] == sid and n["id"] == res.output["note_id"]


async def test_note_errors_are_clear():
    bid, _sid = _book()
    bad = await NOTE.execute({"book_id": bid, "kind": "hint", "title": "", "text": "x"}, _ctx())
    assert not bad.success and "Titel" in bad.error
    place = await NOTE.execute({"book_id": bid, "kind": "hint", "title": "t", "text": "x", "scene_id": "f" * 32}, _ctx())
    assert not place.success and "Stelle" in place.error
    nobook = await NOTE.execute({"book_id": "f" * 32, "kind": "hint", "title": "t", "text": "x"}, _ctx())
    assert not nobook.success and "Buch" in nobook.error


async def test_note_needs_write_role_and_session_project():
    bid, _sid = _book()
    reader = await NOTE.execute({"book_id": bid, "kind": "hint", "title": "t", "text": "x"}, _ctx(user="reader"))
    assert not reader.success and "Leserechte" in reader.error
    other = await NOTE.execute({"book_id": bid, "kind": "hint", "title": "t", "text": "x"}, _ctx(project_id=OTHER_PROJECT_ID))
    assert not other.success
    assert team_notes.list_notes(PROJECT_ID, bid, status="all") == []


async def test_notes_lists_full_text_filtered_and_reader_may_read():
    bid, sid = _book()
    team_notes.add(PROJECT_ID, bid, {"kind": "note", "title": "Quelle", "text": "Langer Text", "author": "Recherche",
                                     "sources": [{"url": "https://example.org"}]})
    team_notes.add(PROJECT_ID, bid, {"kind": "hint", "title": "Szene", "text": "an der Szene", "scene_id": sid, "author": "L"})
    res = await NOTES.execute({"book_id": bid}, _ctx(user="reader"))
    assert res.success and [n["title"] for n in res.output["notes"]] == ["Quelle", "Szene"]
    assert res.output["notes"][0]["sources"][0]["url"] == "https://example.org" and res.output["notes"][0]["text"] == "Langer Text"
    only = await NOTES.execute({"book_id": bid, "scene_id": sid}, _ctx())
    assert [n["title"] for n in only.output["notes"]] == ["Szene"]


async def test_outline_shows_open_notes_per_scene_and_list():
    bid, sid = _book()
    team_notes.add(PROJECT_ID, bid, {"kind": "hint", "title": "A", "text": "a", "scene_id": sid, "author": "P"})
    done = team_notes.add(PROJECT_ID, bid, {"kind": "hint", "title": "B", "text": "b", "scene_id": sid, "author": "P"})
    team_notes.set_status(PROJECT_ID, bid, done["id"], "done")
    o = (await OUTLINE.execute({"book_id": bid}, _ctx())).output
    scene = o["parts"][0]["chapters"][0]["scenes"][0]
    assert scene["open_notes"] == 1
    assert [(n["title"], n["scene_id"]) for n in o["open_notes"]] == [("A", sid)] and "text" not in o["open_notes"][0]
