"""Aus einer Idee einen Task machen: Verknüpfung mit der Tabelle des Tasks-Moduls."""
from __future__ import annotations

import pytest
from helpers import PROJECT_A, TASKS_TABLE, task_row


def _mods():
    from backend import notes, store, task_link
    return store, notes, task_link


def _code(excinfo) -> str:
    return excinfo.value.code


def test_task_entsteht_mit_titel_beschreibung_projekt_und_nutzer():
    store, _, task_link = _mods()
    idea = store.create("alice", title="Admin-Seite", body="alles an einem Ort\n\nmit Übersicht", project_id=PROJECT_A)
    linked = task_link.create("alice", idea["id"])
    task = task_row(linked["task_id"])
    assert task["title"] == "Admin-Seite"
    assert task["description"] == f"Aus Idee {idea['id'][:8]}: Admin-Seite\n\nalles an einem Ort\n\nmit Übersicht"
    assert (task["username"], task["project_id"], task["status"], task["priority"]) == ("alice", PROJECT_A, "open", "medium")
    assert task["session_id"] is None


def test_idee_ohne_beschreibung_und_ohne_projekt():
    store, _, task_link = _mods()
    idea = store.create("alice", title="Nur Kopfzeile")
    task = task_row(task_link.create("alice", idea["id"])["task_id"])
    assert task["description"] == f"Aus Idee {idea['id'][:8]}: Nur Kopfzeile"
    assert task["project_id"] is None


def test_idee_merkt_sich_den_task_und_steht_auf_geplant_mit_anmerkung():
    store, notes, task_link = _mods()
    idea = store.create("alice", title="Admin-Seite")
    linked = task_link.create("alice", idea["id"])
    assert linked["status"] == "planned" and linked["task_id"]
    assert linked["updated_at"] > idea["updated_at"]
    listed = notes.list_for("alice", idea["id"])
    assert [(n["author"], n["body"]) for n in listed] == [
        ("system", f"Task angelegt: {linked['task_id'][:8]}. Status: Neu → Geplant")]
    assert (linked["title"], linked["body"]) == (idea["title"], idea["body"])


def test_schon_geplante_idee_bekommt_keinen_statuswechsel_in_der_anmerkung():
    store, notes, task_link = _mods()
    idea = store.create("alice", title="Schon geplant")
    store.update("alice", idea["id"], status="planned")
    linked = task_link.create("alice", idea["id"])
    assert [n["body"] for n in notes.list_for("alice", idea["id"])] == [f"Task angelegt: {linked['task_id'][:8]}"]


def test_zweiter_versuch_wird_abgelehnt():
    store, notes, task_link = _mods()
    idea = store.create("alice", title="Einmal reicht")
    first = task_link.create("alice", idea["id"])
    with pytest.raises(store.IdeaError) as excinfo:
        task_link.create("alice", idea["id"])
    assert _code(excinfo) == "task_already_linked"
    assert store.get("alice", idea["id"])["task_id"] == first["task_id"]
    assert len(notes.list_for("alice", idea["id"])) == 1


def test_info_nennt_titel_und_status_des_tasks():
    store, _, task_link = _mods()
    idea = store.create("alice", title="Admin-Seite")
    assert task_link.info("alice", idea) is None
    linked = task_link.create("alice", idea["id"])
    assert task_link.info("alice", linked) == {
        "id": linked["task_id"], "short_id": linked["task_id"][:8], "title": "Admin-Seite", "status": "open", "missing": False}


def test_geloeschter_task_wird_als_fehlend_gemeldet_und_ein_neuer_geht():
    from hydrahive.db.connection import db

    store, _, task_link = _mods()
    idea = store.create("alice", title="Task verschwindet")
    linked = task_link.create("alice", idea["id"])
    with db() as conn:
        conn.execute(f"DELETE FROM {TASKS_TABLE} WHERE id = ? AND username = ?", (linked["task_id"], "alice"))
    info = task_link.info("alice", store.get("alice", idea["id"]))
    assert info == {"id": linked["task_id"], "short_id": linked["task_id"][:8], "title": None, "status": None, "missing": True}
    again = task_link.create("alice", idea["id"])
    assert again["task_id"] != linked["task_id"] and task_row(again["task_id"]) is not None


def test_task_eines_anderen_nutzers_gilt_als_fehlend():
    store, _, task_link = _mods()
    foreign = task_link.create("bob", store.create("bob", title="Bobs Idee")["id"])
    idea = store.update("alice", store.create("alice", title="Zeigt auf Bob")["id"], task_id=foreign["task_id"])
    assert task_link.info("alice", idea)["missing"] is True
    assert task_row(foreign["task_id"])["username"] == "bob"


def test_fremde_und_unbekannte_idee():
    store, _, task_link = _mods()
    idea = store.create("alice", title="Privat")
    assert task_link.create("bob", idea["id"]) is None
    assert task_link.create("alice", "gibt-es-nicht") is None
    assert store.get("alice", idea["id"])["task_id"] is None


def test_ohne_tabelle_des_tasks_moduls(monkeypatch):
    store, notes, task_link = _mods()
    idea = store.create("alice", title="Ohne Tasks")
    assert task_link.installed() is True
    monkeypatch.setattr(task_link, "TASKS_TABLE", "module_tasks_gibt_es_nicht")
    assert task_link.installed() is False
    with pytest.raises(store.IdeaError) as excinfo:
        task_link.create("alice", idea["id"])
    assert _code(excinfo) == "tasks_not_installed"
    unchanged = store.get("alice", idea["id"])
    assert (unchanged["task_id"], unchanged["status"]) == (None, "new")
    assert notes.list_for("alice", idea["id"]) == []
    assert task_link.info("alice", {**unchanged, "task_id": "irgendeine-id"})["missing"] is True


def test_scheitert_ein_schritt_bleibt_nichts_halbes_zurueck(monkeypatch):
    from hydrahive.db.connection import db

    store, notes, task_link = _mods()
    idea = store.create("alice", title="Ganz oder gar nicht")

    def kaputt(*args, **kwargs):
        raise RuntimeError("Anmerkung lässt sich nicht schreiben")

    monkeypatch.setattr(notes, "insert", kaputt)
    with pytest.raises(RuntimeError):
        task_link.create("alice", idea["id"])
    unchanged = store.get("alice", idea["id"])
    assert (unchanged["task_id"], unchanged["status"]) == (None, "new")
    with db() as conn:
        left = conn.execute(f"SELECT COUNT(*) FROM {TASKS_TABLE} WHERE title = ?", ("Ganz oder gar nicht",)).fetchone()[0]
    assert left == 0
