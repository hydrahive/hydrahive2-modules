"""Rückverweis vom Task zur Idee: Herkunft (source_kind, source_id) am Task des Tasks-Moduls ab 1.3.0."""
from __future__ import annotations

from helpers import TASKS_TABLE, ensure_old_tasks_table, task_row


def _mods():
    from backend import notes, store, task_link
    return store, notes, task_link


def test_task_traegt_die_idee_als_herkunft():
    store, _, task_link = _mods()
    idea = store.create("alice", title="Mit Rückverweis")
    task = task_row(task_link.create("alice", idea["id"])["task_id"])
    assert (task["source_kind"], task["source_id"]) == ("idea", idea["id"])


def test_aelteres_tasks_modul_ohne_herkunftsspalten(monkeypatch):
    from _hh_isolation import only_own_rows

    store, _, task_link = _mods()
    table = ensure_old_tasks_table()
    monkeypatch.setattr(task_link, "TASKS_TABLE", table)
    idea = store.create("alice", title="Altes Tasks-Modul")
    with only_own_rows(table):
        linked = task_link.create("alice", idea["id"])
        task = task_row(linked["task_id"], table)
        assert task["title"] == "Altes Tasks-Modul" and "source_kind" not in task
        assert linked["status"] == "planned"
        assert task_link.info("alice", linked)["missing"] is False


def _clear_source(task_id: str, kind: str | None = None, source_id: str | None = None) -> None:
    """Zustand wie nach scratchpad 2.1.0: Task ist verknüpft, trägt aber keine Herkunft."""
    from hydrahive.db.connection import db

    with db() as conn:
        conn.execute(f"UPDATE {TASKS_TABLE} SET source_kind = ?, source_id = ? WHERE id = ?", (kind, source_id, task_id))


def test_nachtragen_setzt_die_herkunft_bei_frueher_verknuepften_tasks():
    store, _, task_link = _mods()
    idea = store.create("alice", title="Vor dem Rückverweis verknüpft")
    task_id = task_link.create("alice", idea["id"])["task_id"]
    _clear_source(task_id)
    before = task_row(task_id)
    assert task_link.backfill("alice") == 1
    after = task_row(task_id)
    assert (after["source_kind"], after["source_id"]) == ("idea", idea["id"])
    assert after["updated_at"] == before["updated_at"] and after["description"] == before["description"]
    assert task_link.backfill("alice") == 0


def test_nachtragen_fasst_nur_eigene_und_unbelegte_tasks_an():
    store, _, task_link = _mods()
    mine = task_link.create("alice", store.create("alice", title="Eigene")["id"])["task_id"]
    belegt = task_link.create("alice", store.create("alice", title="Schon belegt")["id"])["task_id"]
    fremd = task_link.create("bob", store.create("bob", title="Von Bob")["id"])["task_id"]
    _clear_source(mine)
    _clear_source(fremd)
    _clear_source(belegt, "ticket", "T-17")
    assert task_link.backfill("alice") == 1
    assert task_row(mine)["source_kind"] == "idea"
    assert (task_row(belegt)["source_kind"], task_row(belegt)["source_id"]) == ("ticket", "T-17")
    assert task_row(fremd)["source_kind"] is None


def test_nachtragen_ohne_spalten_und_ohne_tasks_modul(monkeypatch):
    from _hh_isolation import only_own_rows

    store, _, task_link = _mods()
    table = ensure_old_tasks_table()
    monkeypatch.setattr(task_link, "TASKS_TABLE", table)
    with only_own_rows(table):
        task_link.create("alice", store.create("alice", title="Altes Tasks-Modul")["id"])
        assert task_link.backfill("alice") == 0
    monkeypatch.setattr(task_link, "TASKS_TABLE", "module_tasks_gibt_es_nicht")
    assert task_link.backfill("alice") == 0
