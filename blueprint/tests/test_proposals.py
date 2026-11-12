"""Vorschlag des Agenten neben der Fassung des Nutzers: ablegen, übernehmen, verwerfen, Versionen (Etappe 3a)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from backend import proposals, store, versions
from conftest import PROJECT_A
from hydrahive.db.connection import db

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def graph(count: int, tag: str = "n") -> dict:
    return {"nodes": [{"id": f"{tag}{i}", "type": "flowNode", "position": {"x": 0, "y": 0},
                       "data": {"kind": "flow", "subtype": "action", "label": f"{tag}{i}", "note": ""}}
                      for i in range(count)], "edges": []}


def ids(graph_json: str) -> list[str]:
    return [node["id"] for node in json.loads(graph_json)["nodes"]]


def board_with(count: int, user: str = "testuser", tag: str = "alt") -> int:
    bid = store.create(user, "Board")["id"]
    if count:
        store.update(user, bid, graph_json=json.dumps(graph(count, tag)))
    return bid


def test_migrationen_legen_spalten_und_tabelle_an():
    with db() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(module_blueprint_boards)")}
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"project_id", "proposal_json", "proposal_note", "proposal_at"} <= columns
    assert "module_blueprint_versions" in tables


def test_bestehende_boards_ueberstehen_die_migrationen():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript((MIGRATIONS / "001_blueprint.sql").read_text(encoding="utf-8"))
        conn.execute('INSERT INTO module_blueprint_boards ("user", name, graph_json) VALUES (?, ?, ?)',
                     ("testuser", "Vorher", json.dumps(graph(2))))
        for name in ("002_project_proposal.sql", "003_versions.sql"):
            conn.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))
        row = dict(conn.execute("SELECT * FROM module_blueprint_boards").fetchone())
    finally:
        conn.close()
    assert row["name"] == "Vorher" and ids(row["graph_json"]) == ["n0", "n1"]
    assert row["project_id"] is None and row["proposal_json"] is None and row["proposal_at"] is None


def test_leeres_board_wird_direkt_gezeichnet():
    bid = board_with(0)
    result = proposals.put("testuser", bid, graph(3, "neu"), "erster Entwurf")
    assert result["drawn"] is True
    board = store.get("testuser", bid)
    assert ids(board["graph_json"]) == ["neu0", "neu1", "neu2"]
    assert board["proposal_json"] is None and board["proposal_at"] is None
    assert versions.list_for("testuser", bid) == []


def test_nicht_leeres_board_bekommt_einen_vorschlag_und_bleibt_wie_es_ist():
    bid = board_with(2)
    before = store.get("testuser", bid)
    result = proposals.put("testuser", bid, graph(3, "neu"), "  mit Fehlerfall  ")
    assert result["drawn"] is False
    board = store.get("testuser", bid)
    assert board["graph_json"] == before["graph_json"] and board["updated_at"] == before["updated_at"]
    assert ids(board["proposal_json"]) == ["neu0", "neu1", "neu2"]
    assert board["proposal_note"] == "mit Fehlerfall" and board["proposal_at"]


def test_zweiter_vorschlag_ersetzt_den_ersten():
    bid = board_with(1)
    proposals.put("testuser", bid, graph(2, "a"), "eins")
    proposals.put("testuser", bid, graph(4, "b"), "zwei")
    board = store.get("testuser", bid)
    assert len(ids(board["proposal_json"])) == 4 and board["proposal_note"] == "zwei"


def test_unlesbares_board_wird_nicht_ueberschrieben():
    bid = board_with(0)
    with db() as conn:
        conn.execute("UPDATE module_blueprint_boards SET graph_json = ? WHERE id = ?", ("{kaputt", bid))
    assert proposals.put("testuser", bid, graph(1), "")["drawn"] is False
    assert store.get("testuser", bid)["graph_json"] == "{kaputt"


def test_uebernehmen_legt_die_alte_fassung_in_die_versionen():
    bid = board_with(2)
    proposals.put("testuser", bid, graph(3, "neu"), "Entwurf")
    board = proposals.accept("testuser", bid)
    assert ids(board["graph_json"]) == ["neu0", "neu1", "neu2"]
    assert board["proposal_json"] is None and board["proposal_note"] is None and board["proposal_at"] is None
    listed = versions.list_for("testuser", bid)
    assert [(v["source"], v["node_count"]) for v in listed] == [("proposal", 2)]
    assert "graph_json" not in listed[0]


def test_uebernehmen_ohne_vorschlag_wird_abgelehnt():
    bid = board_with(2)
    with pytest.raises(store.BoardError) as excinfo:
        proposals.accept("testuser", bid)
    assert excinfo.value.code == "no_proposal"


def test_verwerfen_loescht_nur_den_vorschlag():
    bid = board_with(2)
    before = store.get("testuser", bid)["graph_json"]
    proposals.put("testuser", bid, graph(3, "neu"), "Entwurf")
    board = proposals.discard("testuser", bid)
    assert board["proposal_json"] is None and board["graph_json"] == before
    assert versions.list_for("testuser", bid) == []
    assert proposals.discard("testuser", bid)["proposal_json"] is None


def test_nach_21_uebernahmen_liegen_20_versionen_vor():
    bid = board_with(1, tag="start")
    for round_no in range(21):
        proposals.put("testuser", bid, graph(1, f"r{round_no}-"), "")
        proposals.accept("testuser", bid)
    listed = versions.list_for("testuser", bid)
    assert len(listed) == versions.KEEP == 20
    with db() as conn:
        kept = [ids(row["graph_json"])[0] for row in conn.execute(
            "SELECT graph_json FROM module_blueprint_versions WHERE board_id = ? ORDER BY id", (bid,))]
    assert kept[0] == "r0-0" and kept[-1] == "r19-0" and "start0" not in kept


def test_alte_fassung_wiederherstellen():
    bid = board_with(2, tag="alt")
    proposals.put("testuser", bid, graph(3, "neu"), "")
    proposals.accept("testuser", bid)
    version_id = versions.list_for("testuser", bid)[0]["id"]
    board = versions.restore("testuser", bid, version_id)
    assert ids(board["graph_json"]) == ["alt0", "alt1"]
    listed = versions.list_for("testuser", bid)
    assert [(v["source"], v["node_count"]) for v in listed] == [("restore", 3), ("proposal", 2)]


def test_version_eines_anderen_boards_laesst_sich_nicht_wiederherstellen():
    first, second = board_with(1, tag="a"), board_with(1, tag="b")
    proposals.put("testuser", first, graph(2, "x"), "")
    proposals.accept("testuser", first)
    version_id = versions.list_for("testuser", first)[0]["id"]
    assert versions.restore("testuser", second, version_id) is None
    assert ids(store.get("testuser", second)["graph_json"]) == ["b0"]


def test_fremdes_board_ist_unsichtbar():
    bid = board_with(2)
    proposals.put("testuser", bid, graph(3, "neu"), "")
    assert proposals.put("other", bid, graph(1), "") is None
    assert proposals.accept("other", bid) is None
    assert proposals.discard("other", bid) is None
    assert versions.list_for("other", bid) is None
    proposals.accept("testuser", bid)
    version_id = versions.list_for("testuser", bid)[0]["id"]
    assert versions.restore("other", bid, version_id) is None
    assert len(ids(store.get("testuser", bid)["graph_json"])) == 3


def test_board_loeschen_nimmt_die_versionen_mit():
    bid = board_with(2)
    proposals.put("testuser", bid, graph(3), "")
    proposals.accept("testuser", bid)
    assert store.remove("testuser", bid) is True
    with db() as conn:
        left = conn.execute("SELECT COUNT(*) FROM module_blueprint_versions WHERE board_id = ?", (bid,)).fetchone()[0]
    assert left == 0


def test_board_mit_projekt_und_filter_in_der_liste():
    with_project = store.create("testuser", "Mit Projekt", project_id=PROJECT_A)
    without = store.create("testuser", "Ohne Projekt")
    assert with_project["project_id"] == PROJECT_A and without["project_id"] is None
    assert {b["id"] for b in store.list_for("testuser")} == {with_project["id"], without["id"]}
    assert [b["id"] for b in store.list_for("testuser", project_id=PROJECT_A)] == [with_project["id"]]
    assert [b["project_id"] for b in store.list_for("testuser", project_id=PROJECT_A)] == [PROJECT_A]


def test_liste_zeigt_ob_ein_vorschlag_offen_ist():
    bid = board_with(1)
    assert store.list_for("testuser")[0]["has_proposal"] is False
    proposals.put("testuser", bid, graph(2), "")
    row = store.list_for("testuser")[0]
    assert row["has_proposal"] is True and "proposal_json" not in row and "graph_json" not in row


def test_projekt_am_board_aendern_und_entfernen():
    bid = store.create("testuser", "Board")["id"]
    assert store.update("testuser", bid, project_id=PROJECT_A)["project_id"] == PROJECT_A
    assert store.update("testuser", bid, name="Neu")["project_id"] == PROJECT_A
    assert store.update("testuser", bid, project_id=None)["project_id"] is None
