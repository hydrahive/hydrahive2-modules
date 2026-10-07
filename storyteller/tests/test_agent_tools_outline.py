"""Ghostwriter G4d: Agent schlägt Gliederung vor (storyteller_propose_outline)."""
from __future__ import annotations

from pathlib import Path

from backend import proposals_outline as po
from backend import storage
from backend.agent_tools import TOOLS
from conftest import PROJECT_ID

OUTL = next(t for t in TOOLS if t.name == "storyteller_propose_outline")
VIEW = next(t for t in TOOLS if t.name == "storyteller_outline")
CH = [{"title": "Sturm", "scenes": [{"title": "Die Nacht", "summary": "Ein Sturm zieht auf."},
                                    {"title": "Der Morgen", "summary": "Das Boot ist weg.", "pov": "Mia"}]}]


def _ctx(user="testuser", project_id=PROJECT_ID):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess-11", agent_id="a", user_id=user, workspace=Path("/tmp"), project_id=project_id)


def _book():
    return storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})["id"]


async def test_propose_outline_stores_and_reports_counts_book_untouched():
    bid = _book()
    before = storage.get_structure(PROJECT_ID, bid)
    res = await OUTL.execute({"book_id": bid, "chapters": CH, "entities": [{"name": "Kalle", "kind": "character"}],
                              "note": "Teil 2"}, _ctx())
    assert res.success and res.output["chapters"] == 1 and res.output["scenes"] == 2 and res.output["replaced"] is False
    p = po.get(PROJECT_ID, bid)
    assert p["source"] == "agent" and p["session_id"] == "sess-11" and p["note"] == "Teil 2"
    assert storage.get_structure(PROJECT_ID, bid) == before
    res2 = await OUTL.execute({"book_id": bid, "chapters": CH}, _ctx())
    assert res2.output["replaced"] is True


async def test_rejections():
    bid = _book()
    for args in ({"book_id": bid}, {"book_id": bid, "chapters": []}, {"book_id": bid, "chapters": [{"title": "K", "scenes": []}]},
                 {"book_id": bid, "chapters": "Text"}, {"book_id": "f" * 32, "chapters": CH}):
        res = await OUTL.execute(args, _ctx())
        assert not res.success, args
    assert "Zusammenfassung" in (await OUTL.execute({"book_id": bid, "chapters": [{"title": "K", "scenes": [{"title": "S"}]}]}, _ctx())).error
    assert not (await OUTL.execute({"book_id": bid, "chapters": CH}, _ctx(user="reader"))).success
    assert not (await OUTL.execute({"book_id": bid, "chapters": CH}, _ctx(project_id=None))).success
    assert po.find(PROJECT_ID, bid) is None


async def test_outline_view_shows_open_proposal_and_hint():
    bid = _book()
    assert (await VIEW.execute({"book_id": bid}, _ctx())).output["outline_proposal"] is None
    po.store(PROJECT_ID, bid, {"chapters": CH})
    o = (await VIEW.execute({"book_id": bid}, _ctx())).output
    assert o["outline_proposal"] == {"chapters": 1, "scenes": 2, "titles": ["Sturm"]}
    assert "storyteller_propose_outline" in " ".join(t.prompt_hint or "" for t in TOOLS)
