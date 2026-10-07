"""T1a (Task 29fb3911): deutlich kürzerer Vorschlag → Warnung an den Agenten + Hinweis am Vorschlag."""
from __future__ import annotations

import json
from pathlib import Path

from backend import proposals, storage
from backend.agent_tools import TOOLS
from conftest import PROJECT_ID

PROPOSE = next(t for t in TOOLS if t.name == "storyteller_propose_text")


def _ctx():
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id="testuser", workspace=Path("/tmp"), project_id=PROJECT_ID)


def _scene(words: int):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Wort " * words}, base_version=1)
    return b["id"], sid


async def test_much_shorter_proposal_warns_agent_and_marks_proposal():
    bid, sid = _scene(100)
    res = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Wort " * 30}, _ctx())
    assert res.success and res.output["stored"] is True
    assert "kürzer" in res.output["warning"] and "offset" in res.output["warning"]
    p = proposals.get(PROJECT_ID, bid, sid)
    assert p["scene_words"] == 100 and p["words"] == 30


async def test_similar_length_has_no_warning_but_scene_words_recorded():
    bid, sid = _scene(100)
    res = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Wort " * 80}, _ctx())
    assert "warning" not in res.output
    half = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Wort " * 50}, _ctx())
    assert "warning" not in half.output                                  # genau die Hälfte: noch keine Warnung
    assert proposals.get(PROJECT_ID, bid, sid)["scene_words"] == 100


async def test_empty_scene_never_warns():
    bid, sid = _scene(0)
    res = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Ein Satz."}, _ctx())
    assert "warning" not in res.output


def test_old_proposals_without_scene_words_read_as_zero():
    bid, sid = _scene(10)
    proposals.store(PROJECT_ID, bid, sid, "x", run_id="r", model="m", base_version=2)
    meta_path = proposals._paths(PROJECT_ID, bid, sid)[0]           # Ablage wie vor 0.10.2: ohne scene_words
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    del meta["scene_words"]
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    assert proposals.get(PROJECT_ID, bid, sid)["scene_words"] == 0
    assert proposals.list_for_book(PROJECT_ID, bid)[0]["scene_words"] == 0
