"""Ghostwriter G4b: Agent schlägt Szenen-Infos vor (storyteller_propose_scene_info)."""
from __future__ import annotations

from pathlib import Path

from backend import proposals_info, storage
from backend.agent_tools import TOOLS
from conftest import PROJECT_ID

INFO = next(t for t in TOOLS if t.name == "storyteller_propose_scene_info")
OUTLINE = next(t for t in TOOLS if t.name == "storyteller_outline")


def _ctx(user="testuser", project_id=PROJECT_ID):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess-7", agent_id="a", user_id=user, workspace=Path("/tmp"), project_id=project_id)


def _scene():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"title": "Alt", "summary": "Alt."}, base_version=1)
    return b["id"], sid, s


async def test_propose_info_stores_with_agent_source_scene_untouched():
    bid, sid, s = _scene()
    res = await INFO.execute({"book_id": bid, "scene_id": sid, "summary": "Mia findet den Schlüssel.", "pov": "Mia",
                              "note": "aus dem Text"}, _ctx())
    assert res.success and res.output["fields"] == ["summary", "pov"] and res.output["replaced"] is False
    p = proposals_info.get(PROJECT_ID, bid, sid)
    assert p["source"] == "agent" and p["session_id"] == "sess-7" and p["note"] == "aus dem Text"
    assert p["base_version"] == s["version"] and storage.get_scene(PROJECT_ID, bid, sid) == s
    res2 = await INFO.execute({"book_id": bid, "scene_id": sid, "title": "Der Schlüssel"}, _ctx())
    assert res2.output["replaced"] is True


async def test_propose_info_rejections():
    bid, sid, _ = _scene()
    for args in ({"book_id": bid, "scene_id": sid}, {"book_id": bid, "scene_id": sid, "title": "Alt"},
                 {"book_id": bid, "scene_id": sid, "summary": "x" * 2001}, {"book_id": bid, "scene_id": "f" * 32, "title": "N"}):
        res = await INFO.execute(args, _ctx())
        assert not res.success, args
    assert "unverändert" in (await INFO.execute({"book_id": bid, "scene_id": sid, "title": "Alt"}, _ctx())).error
    assert not (await INFO.execute({"book_id": bid, "scene_id": sid, "title": "N"}, _ctx(user="reader"))).success
    assert not (await INFO.execute({"book_id": bid, "scene_id": sid, "title": "N"}, _ctx(project_id=None))).success
    assert proposals_info.list_for_book(PROJECT_ID, bid) == []


async def test_outline_shows_info_proposal_flag_and_hint_names_tool():
    bid, sid, s = _scene()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    o = (await OUTLINE.execute({"book_id": bid}, _ctx())).output
    sc = o["parts"][0]["chapters"][0]["scenes"][0]
    assert sc["has_info_proposal"] is True and sc["has_proposal"] is False
    hints = " ".join(t.prompt_hint or "" for t in TOOLS)
    assert "storyteller_propose_scene_info" in hints
