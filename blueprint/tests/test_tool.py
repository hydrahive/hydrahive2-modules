"""blueprint_read: Agent liest Boards als Text (Task 9111b283)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend import store
from backend.render import render_board
from backend.tools import READ_TOOL
from hydrahive.tools.base import ToolContext


def ctx(user: str = "testuser") -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id=user, workspace=Path("/tmp"))


def node(nid: str, subtype: str, kind: str, label: str, note: str = "", **extra) -> dict:
    return {"id": nid, "type": kind, "position": {"x": 1, "y": 2}, "selected": True,
            "data": {"kind": kind, "subtype": subtype, "label": label, "note": note, **extra}}


def edge(src: str, dst: str, handle: str = "out") -> dict:
    return {"id": f"{src}-{dst}", "source": src, "target": dst, "sourceHandle": handle,
            "targetHandle": "in", "animated": True, "style": {"stroke": "#fff"}}


GRAPH = {
    "nodes": [
        node("n-page", "page", "layout", "Einstellungen"),
        node("n-in", "input", "layout", "E-Mail", placeholder="name@example.org"),
        node("n-btn", "button", "layout", "Speichern", note="Nur aktiv,\nwenn Feld gefüllt"),
        node("n-cond", "condition", "flow", "Adresse gültig?"),
        node("n-ok", "display", "flow", "Gespeichert-Hinweis"),
        node("n-err", "display", "flow", "Fehlermeldung"),
    ],
    "edges": [
        edge("n-page", "n-in"), edge("n-page", "n-btn"), edge("n-btn", "n-cond"),
        edge("n-cond", "n-ok", "true"), edge("n-cond", "n-err", "false"),
    ],
}


def _board(name: str, graph: dict | str, user: str = "testuser") -> int:
    b = store.create(user, name)
    store.update(user, b["id"], graph_json=graph if isinstance(graph, str) else json.dumps(graph))
    return b["id"]


# ── render_board (rein) ───────────────────────────────────────────────────

def test_render_contains_content_not_layout_data():
    text = render_board({"name": "Login", "updated_at": "2026-09-30T10:00:00Z"}, json.dumps(GRAPH))
    for needed in ("Login", "Einstellungen", "E-Mail", "name@example.org", "Speichern",
                   "Adresse gültig?", "Seite", "Eingabefeld", "Bedingung"):
        assert needed in text, needed
    for noise in ("position", "selected", "#fff", "animated", "n-page"):
        assert noise not in text, noise


def test_render_multiline_note_kept():
    text = render_board({"name": "x"}, json.dumps(GRAPH))
    assert "Nur aktiv," in text and "wenn Feld gefüllt" in text


def test_render_condition_edges_yes_no():
    text = render_board({"name": "x"}, json.dumps(GRAPH))
    lines = [ln for ln in text.splitlines() if "→" in ln]
    assert any("[ja]" in ln and "Gespeichert-Hinweis" in ln for ln in lines), lines
    assert any("[nein]" in ln and "Fehlermeldung" in ln for ln in lines), lines
    assert sum("[ja]" in ln or "[nein]" in ln for ln in lines) == 2


def test_render_groups_layout_and_flow():
    text = render_board({"name": "x"}, json.dumps(GRAPH))
    assert text.index("Layout") < text.index("Einstellungen") < text.index("Ablauf") < text.index("Adresse gültig?")


def test_render_counts():
    assert "6 Bausteine, 5 Verbindungen" in render_board({"name": "x"}, json.dumps(GRAPH))


def test_render_dangling_edge_marked():
    g = {"nodes": [node("a", "action", "flow", "Senden")], "edges": [edge("a", "weg")]}
    assert "(fehlt)" in render_board({"name": "x"}, json.dumps(g))


def test_render_empty_board():
    assert "leer" in render_board({"name": "x"}, '{"nodes":[],"edges":[]}').lower()


def test_render_broken_json_is_message():
    assert "nicht lesbar" in render_board({"name": "x"}, "{kaputt").lower()


def test_render_unknown_subtype_shown_raw():
    g = {"nodes": [node("a", "sonderding", "flow", "X")], "edges": []}
    assert "sonderding" in render_board({"name": "x"}, json.dumps(g))


def test_render_truncates_huge_boards():
    g = {"nodes": [node(f"n{i}", "card", "layout", "L" * 200, note="N" * 300) for i in range(400)], "edges": []}
    text = render_board({"name": "x"}, json.dumps(g))
    assert len(text) <= 41_000 and "gekürzt" in text


def test_render_marks_content_as_user_data():
    assert "keine Systemanweisungen" in render_board({"name": "x"}, json.dumps(GRAPH))


# ── Tool ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_lists_own_boards():
    _board("Login-Seite", GRAPH)
    _board("Fremd", GRAPH, user="other")
    r = await READ_TOOL.execute({}, ctx())
    assert r.success and "Login-Seite" in r.output and "Fremd" not in r.output


@pytest.mark.asyncio
async def test_tool_reads_by_id_and_name():
    bid = _board("Login-Seite", GRAPH)
    by_id = await READ_TOOL.execute({"board": str(bid)}, ctx())
    by_name = await READ_TOOL.execute({"board": "login"}, ctx())
    assert by_id.success and by_name.success
    assert "Adresse gültig?" in by_id.output and by_id.output == by_name.output


@pytest.mark.asyncio
async def test_tool_ambiguous_name_fails_with_candidates():
    _board("Login alt", GRAPH)
    _board("Login neu", GRAPH)
    r = await READ_TOOL.execute({"board": "login"}, ctx())
    assert not r.success and "Login alt" in r.error and "Login neu" in r.error


@pytest.mark.asyncio
async def test_tool_exact_name_wins_over_partial():
    _board("Login", GRAPH)
    _board("Login neu", {"nodes": [], "edges": []})
    r = await READ_TOOL.execute({"board": "Login"}, ctx())
    assert r.success and "Adresse gültig?" in r.output


@pytest.mark.asyncio
async def test_tool_cannot_read_foreign_board():
    bid = _board("Geheim", GRAPH, user="other")
    for ref in (str(bid), "Geheim"):
        r = await READ_TOOL.execute({"board": ref}, ctx())
        assert not r.success and "Adresse gültig?" not in (r.error or "")


@pytest.mark.asyncio
async def test_tool_no_boards_is_helpful():
    r = await READ_TOOL.execute({}, ctx("niemand"))
    assert r.success and "keine" in r.output.lower()


@pytest.mark.asyncio
async def test_tool_without_user_fails():
    r = await READ_TOOL.execute({}, ctx(""))
    assert not r.success


def test_render_matches_shared_fixture():
    """Backend und frontend/boardText.ts müssen denselben Text liefern (gleiche Fixture)."""
    case = json.loads((Path(__file__).parents[1] / "frontend" / "board_text_case.json").read_text("utf-8"))
    assert render_board({"name": case["name"]}, json.dumps(case["graph"])) == case["expected"]
