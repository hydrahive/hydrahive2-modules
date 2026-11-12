"""Aus einer Idee ein Blueprint-Board machen: Verknüpfung mit der Tabelle des Blueprint-Moduls (Etappe 3a)."""
from __future__ import annotations

import pytest
from helpers import BOARDS_TABLE, PROJECT_A, board_row, ensure_old_boards_table


def _mods():
    from backend import board_link, notes, store
    return store, notes, board_link


def _count(user: str = "alice", table: str = BOARDS_TABLE) -> int:
    from hydrahive.db.connection import db

    with db() as conn:
        return conn.execute(f'SELECT COUNT(*) FROM {table} WHERE "user" = ?', (user,)).fetchone()[0]


def test_board_entsteht_mit_name_projekt_und_nutzer_der_idee():
    store, _, board_link = _mods()
    idea = store.create("alice", title="Admin-Seite", body="alles an einem Ort", project_id=PROJECT_A)
    linked, created = board_link.create("alice", idea["id"])
    board = board_row(linked["board_id"])
    assert created is True
    assert (board["user"], board["name"], board["project_id"]) == ("alice", "Admin-Seite", PROJECT_A)
    assert board["graph_json"] == '{"nodes":[],"edges":[]}' and board["proposal_json"] is None
    # Der Text der Idee bleibt, wie er ist; nur der Verweis kommt dazu.
    assert (linked["title"], linked["body"], linked["status"]) == (idea["title"], idea["body"], "new")
    assert linked["updated_at"] > idea["updated_at"]


def test_idee_ohne_projekt_und_mit_langer_kopfzeile():
    store, _, board_link = _mods()
    idea = store.create("alice", title="x" * 200)
    board = board_row(board_link.create("alice", idea["id"])[0]["board_id"])
    assert board["project_id"] is None
    assert board["name"] == "x" * 120  # Board-Namen sind kürzer als Kopfzeilen


def test_anmerkung_haelt_das_anlegen_fest():
    store, notes, board_link = _mods()
    idea = store.create("alice", title="Admin-Seite")
    linked, _ = board_link.create("alice", idea["id"])
    listed = notes.list_for("alice", idea["id"])
    assert [(n["author"], n["body"]) for n in listed] == [("system", f"Board angelegt: ID {linked['board_id']}")]


def test_zweiter_aufruf_liefert_dasselbe_board():
    store, notes, board_link = _mods()
    idea = store.create("alice", title="Einmal reicht")
    first, _ = board_link.create("alice", idea["id"])
    again, created = board_link.create("alice", idea["id"])
    assert created is False and again["board_id"] == first["board_id"]
    assert _count() == 1 and len(notes.list_for("alice", idea["id"])) == 1
    assert again["updated_at"] == first["updated_at"]


def test_info_nennt_name_und_offenen_vorschlag():
    from hydrahive.db.connection import db

    store, _, board_link = _mods()
    idea = store.create("alice", title="Admin-Seite")
    assert board_link.info("alice", idea) is None
    linked, _ = board_link.create("alice", idea["id"])
    expected = {"id": linked["board_id"], "name": "Admin-Seite", "has_proposal": False, "missing": False}
    assert board_link.info("alice", linked) == expected
    with db() as conn:
        conn.execute(f"UPDATE {BOARDS_TABLE} SET name = ?, proposal_json = ? WHERE id = ?",
                     ("Umbenannt", '{"nodes":[],"edges":[]}', linked["board_id"]))
    assert board_link.info("alice", linked) == {**expected, "name": "Umbenannt", "has_proposal": True}


def test_geloeschtes_board_gilt_als_fehlend_und_ein_neues_geht():
    from hydrahive.db.connection import db

    store, _, board_link = _mods()
    idea = store.create("alice", title="Board verschwindet")
    linked, _ = board_link.create("alice", idea["id"])
    with db() as conn:
        conn.execute(f'DELETE FROM {BOARDS_TABLE} WHERE id = ? AND "user" = ?', (linked["board_id"], "alice"))
    info = board_link.info("alice", store.get("alice", idea["id"]))
    assert info == {"id": linked["board_id"], "name": None, "has_proposal": False, "missing": True}
    again, created = board_link.create("alice", idea["id"])
    assert created is True and again["board_id"] != linked["board_id"] and board_row(again["board_id"]) is not None


def test_board_eines_anderen_nutzers_gilt_als_fehlend():
    store, _, board_link = _mods()
    foreign, _ = board_link.create("bob", store.create("bob", title="Bobs Idee")["id"])
    idea = store.update("alice", store.create("alice", title="Zeigt auf Bob")["id"], board_id=foreign["board_id"])
    assert board_link.info("alice", idea)["missing"] is True
    # Ein neues Board entsteht für alice, Bobs Board bleibt unberührt.
    again, created = board_link.create("alice", idea["id"])
    assert created is True and again["board_id"] != foreign["board_id"]
    assert board_row(foreign["board_id"])["user"] == "bob" and _count("bob") == 1


def test_fremde_und_unbekannte_idee():
    store, _, board_link = _mods()
    idea = store.create("alice", title="Privat")
    assert board_link.create("bob", idea["id"]) is None
    assert board_link.create("alice", "gibt-es-nicht") is None
    assert store.get("alice", idea["id"])["board_id"] is None and _count("bob") == 0


def test_ohne_tabelle_des_blueprint_moduls(monkeypatch):
    store, notes, board_link = _mods()
    idea = store.create("alice", title="Ohne Blueprint")
    assert board_link.installed() is True
    monkeypatch.setattr(board_link, "BOARDS_TABLE", "module_blueprint_gibt_es_nicht")
    assert board_link.installed() is False
    with pytest.raises(store.IdeaError) as excinfo:
        board_link.create("alice", idea["id"])
    assert excinfo.value.code == "blueprint_not_installed"
    unchanged = store.get("alice", idea["id"])
    assert unchanged["board_id"] is None and unchanged["updated_at"] == idea["updated_at"]
    assert notes.list_for("alice", idea["id"]) == []
    assert board_link.info("alice", {**unchanged, "board_id": 7})["missing"] is True


def test_aelteres_blueprint_ohne_projekt_bekommt_das_board_trotzdem(monkeypatch):
    store, _, board_link = _mods()
    old = ensure_old_boards_table()
    monkeypatch.setattr(board_link, "BOARDS_TABLE", old)
    idea = store.create("alice", title="Altes Blueprint", project_id=PROJECT_A)
    linked, created = board_link.create("alice", idea["id"])
    board = board_row(linked["board_id"], old)
    assert created is True and board["name"] == "Altes Blueprint" and "project_id" not in board
    assert board_link.info("alice", linked) == {
        "id": linked["board_id"], "name": "Altes Blueprint", "has_proposal": False, "missing": False}


def test_obergrenze_des_blueprint_moduls_gilt_auch_hier(monkeypatch):
    store, notes, board_link = _mods()
    monkeypatch.setattr(board_link, "MAX_BOARDS", 2)
    for title in ("eins", "zwei"):
        board_link.create("alice", store.create("alice", title=title)["id"])
    third = store.create("alice", title="drei")
    with pytest.raises(store.IdeaError) as excinfo:
        board_link.create("alice", third["id"])
    assert excinfo.value.code == "boards_full"
    assert _count() == 2 and store.get("alice", third["id"])["board_id"] is None
    assert notes.list_for("alice", third["id"]) == []
    # Die Grenze gilt je Nutzer.
    assert board_link.create("bob", store.create("bob", title="Bob")["id"])[1] is True


def test_scheitert_ein_schritt_bleibt_nichts_halbes_zurueck(monkeypatch):
    store, notes, board_link = _mods()
    idea = store.create("alice", title="Ganz oder gar nicht")

    def kaputt(*args, **kwargs):
        raise RuntimeError("Anmerkung lässt sich nicht schreiben")

    monkeypatch.setattr(notes, "insert", kaputt)
    with pytest.raises(RuntimeError):
        board_link.create("alice", idea["id"])
    assert store.get("alice", idea["id"])["board_id"] is None and _count() == 0


def test_idee_loeschen_laesst_das_board_stehen():
    store, _, board_link = _mods()
    idea = store.create("alice", title="Idee geht, Board bleibt")
    linked, _ = board_link.create("alice", idea["id"])
    assert store.delete("alice", idea["id"]) is True
    assert board_row(linked["board_id"])["name"] == "Idee geht, Board bleibt"


def test_zwei_gleichzeitige_aufrufe_ergeben_ein_board(monkeypatch):
    """Doppelklick: Der zweite Aufruf wartet, bis der erste fertig ist, und bekommt dessen Board."""
    import threading
    import time

    store, notes, board_link = _mods()
    idea = store.create("alice", title="Doppelklick")
    insert = board_link._insert_board

    def slow_insert(conn, username, row):
        board_id = insert(conn, username, row)
        time.sleep(0.4)  # hält die Transaktion offen, bis der zweite Aufruf unterwegs ist
        return board_id

    monkeypatch.setattr(board_link, "_insert_board", slow_insert)
    results: list = []

    def call():
        try:
            results.append(board_link.create("alice", idea["id"]))
        except Exception as exc:  # noqa: BLE001 - der Test will jede Ausnahme sehen
            results.append(exc)

    threads = [threading.Thread(target=call) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert all(isinstance(result, tuple) for result in results), results
    assert sorted(created for _, created in results) == [False, True]
    assert len({linked["board_id"] for linked, _ in results}) == 1
    assert _count() == 1 and len(notes.list_for("alice", idea["id"])) == 1
