"""Ghostwriter G4a: Agent schlägt Szenentext vor (Spec §11.1/§11.2) – Szene bleibt unberührt."""
from __future__ import annotations

from pathlib import Path

from conftest import PROJECT_ID

from backend import proposals, storage
from backend.agent_tools import TOOLS


def _ctx(user="testuser", project_id=PROJECT_ID, session="sess-42"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id=session, agent_id="a", user_id=user, workspace=Path("/tmp"), project_id=project_id)


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Original vom Autor."}, base_version=1)
    return b["id"], sid, s


PROPOSE = next(t for t in TOOLS if t.name == "storyteller_propose_text")


async def test_propose_stores_proposal_with_agent_source_and_leaves_scene():
    bid, sid, s = _book()
    res = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "  Neue Fassung vom Agenten.  ", "note": "kürzer"}, _ctx())
    assert res.success and res.output["stored"] is True and res.output["replaced"] is False and res.output["words"] == 4
    assert storage.get_scene(PROJECT_ID, bid, sid) == s                       # Szene unverändert
    p = proposals.get(PROJECT_ID, bid, sid)
    assert p["text"] == "Neue Fassung vom Agenten." and p["source"] == "agent" and p["session_id"] == "sess-42"
    assert p["base_version"] == s["version"] and p["note"] == "kürzer"


async def test_second_proposal_replaces_and_says_so():
    bid, sid, _ = _book()
    await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Erst."}, _ctx())
    res = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Zweit."}, _ctx())
    assert res.output["replaced"] is True and proposals.get(PROJECT_ID, bid, sid)["text"] == "Zweit."


async def test_reader_cannot_propose():
    bid, sid, _ = _book()
    res = await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "X"}, _ctx(user="reader"))
    assert not res.success and "Leserechte" in res.error
    assert proposals.list_for_book(PROJECT_ID, bid) == []


async def test_non_member_and_no_project():
    bid, sid, _ = _book()
    assert not (await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "X"}, _ctx(user="other"))).success
    assert not (await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "X"}, _ctx(project_id=None))).success
    assert proposals.list_for_book(PROJECT_ID, bid) == []


async def test_empty_unknown_and_too_long_are_rejected():
    bid, sid, _ = _book()
    for args in ({"book_id": bid, "scene_id": sid, "text": "   "}, {"book_id": bid, "scene_id": sid},
                 {"book_id": bid, "scene_id": "f" * 32, "text": "X"}, {"book_id": "f" * 32, "scene_id": sid, "text": "X"},
                 {"book_id": bid, "scene_id": "../x", "text": "X"},
                 {"book_id": bid, "scene_id": sid, "text": "x" * (storage.MAX_SCENE_BYTES + 1)}):
        res = await PROPOSE.execute(args, _ctx())
        assert not res.success, args
    assert proposals.list_for_book(PROJECT_ID, bid) == []


async def test_agent_proposal_is_accepted_like_others():
    bid, sid, s = _book()
    await PROPOSE.execute({"book_id": bid, "scene_id": sid, "text": "Vom Agenten."}, _ctx())
    scene = proposals.accept(PROJECT_ID, bid, sid, base_version=s["version"])
    assert scene["text"] == "Vom Agenten." and scene["origin"] == "ai_draft"


def test_old_proposals_without_source_read_as_run():
    bid, sid, s = _book()
    proposals.store(PROJECT_ID, bid, sid, "alt", run_id="r", model="m", base_version=s["version"])
    meta = storage.book_dir(PROJECT_ID, bid) / "proposals" / f"{sid}.json"
    import json
    raw = json.loads(meta.read_text())
    for k in ("source", "session_id", "note"):
        raw.pop(k, None)
    meta.write_text(json.dumps(raw))
    assert proposals.get(PROJECT_ID, bid, sid)["source"] == "run"
    assert proposals.list_for_book(PROJECT_ID, bid)[0]["source"] == "run"
