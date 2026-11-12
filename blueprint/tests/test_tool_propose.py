"""blueprint_propose: Der Agent legt einen Entwurf als Vorschlag ab (Etappe 3a)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend import proposals, store
from backend.tools import READ_TOOL
from backend.tools_propose import PROPOSE_TOOL
from conftest import PROJECT_A, PROJECT_B
from hydrahive.tools.base import ToolContext

NODES = [
    {"key": "seite", "type": "page", "label": "Ideen"},
    {"key": "knopf", "type": "button", "label": "Speichern"},
    {"key": "frage", "type": "condition", "label": "Kopfzeile gefüllt?"},
    {"key": "ok", "type": "action", "label": "Idee anlegen"},
    {"key": "fehler", "type": "display", "label": "Hinweis zeigen"},
]
EDGES = [
    {"from": "seite", "to": "knopf"}, {"from": "knopf", "to": "frage"},
    {"from": "frage", "to": "ok", "branch": "ja"}, {"from": "frage", "to": "fehler", "branch": "nein"},
]
OLD = {"nodes": [{"id": "alt", "type": "flowNode", "position": {"x": 0, "y": 0},
                  "data": {"kind": "flow", "subtype": "action", "label": "Alt", "note": ""}}], "edges": []}


def ctx(user: str = "testuser", project_id: str | None = None) -> ToolContext:
    return ToolContext(session_id="s1", agent_id="a1", user_id=user, workspace=Path("/tmp"), project_id=project_id)


def ids(graph_json: str) -> list[str]:
    return [node["id"] for node in json.loads(graph_json)["nodes"]]


def _board(name: str = "Board", graph: dict | None = None, user: str = "testuser") -> int:
    bid = store.create(user, name)["id"]
    if graph is not None:
        store.update(user, bid, graph_json=json.dumps(graph))
    return bid


async def _propose(args: dict, context: ToolContext | None = None):
    return await PROPOSE_TOOL.execute({"nodes": NODES, "edges": EDGES, **args}, context or ctx())


@pytest.mark.asyncio
async def test_neues_board_wird_angelegt_und_direkt_gezeichnet():
    result = await _propose({"name": "Ideen festhalten", "note": "erster Entwurf"})
    assert result.success, result.error
    boards = store.list_for("testuser")
    assert [b["name"] for b in boards] == ["Ideen festhalten"]
    board = store.get("testuser", boards[0]["id"])
    assert ids(board["graph_json"]) == ["seite", "knopf", "frage", "ok", "fehler"]
    assert board["proposal_json"] is None
    assert f"ID {board['id']}" in result.output and "5 Bausteine, 4 Verbindungen" in result.output
    assert f"/blueprint?board={board['id']}" in result.output


@pytest.mark.asyncio
async def test_neues_board_uebernimmt_das_projekt_der_sitzung():
    assert (await _propose({"name": "Mit Projekt"}, ctx(project_id=PROJECT_A))).success
    assert store.list_for("testuser")[0]["project_id"] == PROJECT_A


@pytest.mark.asyncio
async def test_fremdes_projekt_der_sitzung_wird_nicht_uebernommen():
    result = await _propose({"name": "Ohne Projekt"}, ctx(project_id=PROJECT_B))
    assert result.success, result.error
    assert store.list_for("testuser")[0]["project_id"] is None


@pytest.mark.asyncio
async def test_leeres_vorhandenes_board_wird_direkt_gezeichnet():
    bid = _board("Leer")
    result = await _propose({"board": str(bid)})
    assert result.success and "direkt gezeichnet" in result.output
    assert len(ids(store.get("testuser", bid)["graph_json"])) == 5


@pytest.mark.asyncio
async def test_board_mit_inhalt_bekommt_einen_vorschlag_und_bleibt_unveraendert():
    bid = _board("Mit Inhalt", OLD)
    result = await _propose({"board": str(bid), "note": "mit Fehlerfall"})
    assert result.success, result.error
    board = store.get("testuser", bid)
    assert ids(board["graph_json"]) == ["alt"]
    assert len(ids(board["proposal_json"])) == 5 and board["proposal_note"] == "mit Fehlerfall"
    assert "Vorschlag" in result.output and "unverändert" in result.output
    assert "übernimmt oder verwirft" in result.output and "ersetzt" not in result.output


@pytest.mark.asyncio
async def test_zweiter_vorschlag_nennt_dass_der_erste_ersetzt_wurde():
    bid = _board("Mit Inhalt", OLD)
    await _propose({"board": str(bid)})
    result = await _propose({"board": str(bid)})
    assert result.success and "ersetzt" in result.output


@pytest.mark.asyncio
async def test_board_ueber_den_namen():
    bid = _board("Login-Seite", OLD)
    assert (await _propose({"board": "login"})).success
    assert store.get("testuser", bid)["proposal_json"] is not None


@pytest.mark.asyncio
async def test_mehrdeutiger_name_nennt_die_treffer():
    _board("Login alt", OLD)
    _board("Login neu", OLD)
    result = await _propose({"board": "login"})
    assert not result.success and "Login alt" in result.error and "Login neu" in result.error


@pytest.mark.asyncio
async def test_fremdes_board_ist_unerreichbar():
    bid = _board("Geheim", OLD, user="other")
    for ref in (str(bid), "Geheim"):
        result = await _propose({"board": ref})
        assert not result.success
    assert store.get("other", bid)["proposal_json"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [{}, {"board": "1", "name": "Neu"}, {"name": "   "}, {"board": "  "}])
async def test_genau_eines_von_board_und_name(args):
    result = await _propose(args)
    assert not result.success and "board" in result.error and "name" in result.error
    assert store.list_for("testuser") == []


@pytest.mark.asyncio
async def test_zu_langer_name_wird_abgelehnt():
    result = await _propose({"name": "x" * 121})
    assert not result.success and "120" in result.error
    assert store.list_for("testuser") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("note", ["x" * 501, 7, ["Liste"]])
async def test_zu_lange_oder_falsche_notiz_wird_abgelehnt_statt_gekuerzt(note):
    result = await _propose({"name": "Neu", "note": note})
    assert not result.success and "500" in result.error
    assert store.list_for("testuser") == []


@pytest.mark.asyncio
async def test_unbrauchbarer_vorschlag_legt_nichts_an_und_sagt_warum():
    result = await PROPOSE_TOOL.execute(
        {"name": "Neu", "nodes": [{"key": "a", "type": "sonderding", "label": "X"}], "edges": []}, ctx())
    assert not result.success and "sonderding" in result.error and "agent_tool" in result.error
    assert store.list_for("testuser") == []
    bid = _board("Mit Inhalt", OLD)
    result = await PROPOSE_TOOL.execute(
        {"board": str(bid), "nodes": NODES, "edges": [{"from": "seite", "to": "gibt_es_nicht"}]}, ctx())
    assert not result.success and store.get("testuser", bid)["proposal_json"] is None


@pytest.mark.asyncio
async def test_ohne_nutzer_geht_nichts():
    assert not (await _propose({"name": "Neu"}, ctx(""))).success


@pytest.mark.asyncio
async def test_volle_boardliste_wird_gemeldet(monkeypatch):
    monkeypatch.setattr(store, "_MAX", 1)
    _board("Schon da")
    result = await _propose({"name": "Zu viel"})
    assert not result.success and "Boards" in result.error
    assert len(store.list_for("testuser")) == 1


@pytest.mark.asyncio
async def test_blueprint_read_nennt_einen_offenen_vorschlag():
    bid = _board("Mit Inhalt", OLD)
    ohne = await READ_TOOL.execute({"board": str(bid)}, ctx())
    assert "Vorschlag" not in ohne.output
    await _propose({"board": str(bid), "note": "mit Fehlerfall"})
    mit = await READ_TOOL.execute({"board": str(bid)}, ctx())
    assert "Offener Vorschlag" in mit.output and "5 Bausteine" in mit.output and "mit Fehlerfall" in mit.output
    # Gelesen wird weiter die Fassung des Nutzers, nicht der Vorschlag.
    assert "„Alt“" in mit.output and "Kopfzeile gefüllt?" not in mit.output


def test_werkzeuge_sind_angemeldet():
    from backend import register

    class Ctx:
        def __init__(self):
            self.tools, self.routers, self.migrations = [], [], None

        def register_tool(self, tool):
            self.tools.append(tool.name)

        def register_router(self, router):
            self.routers.append(router)

        def register_migrations(self, rel):
            self.migrations = rel

    context = Ctx()
    register(context)
    assert sorted(context.tools) == ["blueprint_propose", "blueprint_read"]
    assert context.migrations == "migrations" and len(context.routers) == 1


def test_beschreibung_und_schema_nennen_arten_und_grenzen():
    from backend import catalog

    assert PROPOSE_TOOL.name == "blueprint_propose" and PROPOSE_TOOL.category == "blueprint"
    kinds = PROPOSE_TOOL.schema["properties"]["nodes"]["items"]["properties"]["type"]["enum"]
    assert kinds == list(catalog.SUBTYPES)
    assert PROPOSE_TOOL.schema["required"] == ["nodes"]
    assert "Koordinaten" in PROPOSE_TOOL.description
    assert "blueprint_propose" in PROPOSE_TOOL.prompt_hint


def test_put_meldet_ob_ein_aelterer_vorschlag_ersetzt_wurde():
    bid = _board("Mit Inhalt", OLD)
    graph = {"nodes": OLD["nodes"], "edges": []}
    assert proposals.put("testuser", bid, graph, "")["replaced"] is False
    assert proposals.put("testuser", bid, graph, "")["replaced"] is True
