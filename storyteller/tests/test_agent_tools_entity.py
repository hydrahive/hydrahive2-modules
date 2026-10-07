"""Ghostwriter G4c: Agent schlägt Steckbriefe vor (storyteller_propose_entity)."""
from __future__ import annotations

from pathlib import Path

from backend import proposals_entities as pe
from backend import storage
from backend.agent_tools import TOOLS
from conftest import PROJECT_ID

ENT = next(t for t in TOOLS if t.name == "storyteller_propose_entity")
OUTLINE = next(t for t in TOOLS if t.name == "storyteller_outline")
MIA = "e" * 32


def _ctx(user="testuser", project_id=PROJECT_ID):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess-9", agent_id="a", user_id=user, workspace=Path("/tmp"), project_id=project_id)


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": MIA, "kind": "character", "name": "Mia", "aliases": [], "description": "Zwölf.", "fields": []}]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    return b["id"]


async def test_new_and_change_with_agent_source_structure_untouched():
    bid = _book()
    before = storage.get_structure(PROJECT_ID, bid)
    res = await ENT.execute({"book_id": bid, "kind": "character", "name": "Hinnerk", "aliases": ["Großvater"],
                             "description": "Leuchtturmwärter.", "fields": [{"key": "Alter", "value": "71"}], "note": "aus Szene 1"}, _ctx())
    assert res.success and res.output["new"] is True and res.output["fields"] == ["name", "aliases", "description", "fields"]
    res2 = await ENT.execute({"book_id": bid, "entity_id": MIA, "description": "Zwölf, mutig."}, _ctx())
    assert res2.success and res2.output["new"] is False and res2.output["replaced"] is False
    props = pe.list_for_book(PROJECT_ID, bid)
    assert {p["source"] for p in props} == {"agent"} and {p["session_id"] for p in props} == {"sess-9"}
    assert storage.get_structure(PROJECT_ID, bid) == before
    res3 = await ENT.execute({"book_id": bid, "entity_id": MIA, "description": "Zwölf, sehr mutig."}, _ctx())
    assert res3.output["replaced"] is True and len(pe.list_for_book(PROJECT_ID, bid)) == 2


async def test_existing_name_tells_agent_the_id_and_other_rejections():
    bid = _book()
    res = await ENT.execute({"book_id": bid, "kind": "character", "name": "mia"}, _ctx())
    assert not res.success and MIA in res.error and "entity_id" in res.error
    for args in ({"book_id": bid, "name": "X"}, {"book_id": bid, "entity_id": MIA, "description": "Zwölf."},
                 {"book_id": bid, "entity_id": "f" * 32, "description": "x"}, {"book_id": bid, "kind": "x", "name": "Y"},
                 {"book_id": "f" * 32, "kind": "item", "name": "Z"}):
        assert not (await ENT.execute(args, _ctx())).success, args
    assert not (await ENT.execute({"book_id": bid, "kind": "item", "name": "Z"}, _ctx(user="reader"))).success
    assert not (await ENT.execute({"book_id": bid, "kind": "item", "name": "Z"}, _ctx(project_id=None))).success
    assert pe.list_for_book(PROJECT_ID, bid) == []


async def test_outline_lists_open_entity_proposals_and_hint():
    bid = _book()
    pe.store(PROJECT_ID, bid, None, {"kind": "place", "name": "Leuchtturm"})
    pe.store(PROJECT_ID, bid, MIA, {"description": "Neu"})
    o = (await OUTLINE.execute({"book_id": bid}, _ctx())).output
    assert sorted((p["entity_id"], p["name"]) for p in o["entity_proposals"]) == [("", "Leuchtturm"), (MIA, "Mia")]
    assert "storyteller_propose_entity" in " ".join(t.prompt_hint or "" for t in TOOLS)
