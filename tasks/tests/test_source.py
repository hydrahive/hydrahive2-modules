"""Herkunft eines Tasks (source_kind, source_id): Rückverweis auf das, woraus er entstanden ist."""
from __future__ import annotations

from pathlib import Path

import pytest
from hydrahive.db.connection import db
from hydrahive.tools.base import ToolContext

BASE = "/api/modules/tasks/tasks"
IDEA_ID = "aaaa1111-0000-4000-8000-000000000001"


def _ctx(username: str = "alice") -> ToolContext:
    return ToolContext(session_id="sess-1", agent_id="agent-1", user_id=username, workspace=Path("/tmp"))


def _set_source(task_id: str, kind: str | None, source_id: str | None) -> None:
    with db() as conn:
        conn.execute("UPDATE module_tasks SET source_kind = ?, source_id = ? WHERE id = ?", (kind, source_id, task_id))


def test_migration_legt_die_spalten_an():
    with db() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(module_tasks)")}
    assert {"source_kind", "source_id"} <= columns


def test_neuer_task_hat_keine_herkunft(client, alice):
    task = client.post(BASE, json={"title": "Ohne Herkunft"}, headers=alice).json()
    assert task["source_kind"] is None and task["source_id"] is None


def test_herkunft_ist_ueber_die_route_nicht_setzbar(client, alice):
    created = client.post(BASE, json={"title": "Gefälscht", "source_kind": "idea", "source_id": IDEA_ID}, headers=alice).json()
    assert created["source_kind"] is None and created["source_id"] is None
    patched = client.patch(f"{BASE}/{created['id']}", json={"source_kind": "idea", "source_id": IDEA_ID}, headers=alice).json()
    assert patched["source_kind"] is None and patched["source_id"] is None


def test_liste_liefert_die_herkunft_mit(client, alice):
    task = client.post(BASE, json={"title": "Aus Idee"}, headers=alice).json()
    _set_source(task["id"], "idea", IDEA_ID)
    listed = client.get(BASE, headers=alice).json()
    assert [(t["source_kind"], t["source_id"]) for t in listed] == [("idea", IDEA_ID)]


def test_aendern_laesst_die_herkunft_stehen(client, alice):
    task = client.post(BASE, json={"title": "Aus Idee"}, headers=alice).json()
    _set_source(task["id"], "idea", IDEA_ID)
    changed = client.patch(f"{BASE}/{task['id']}", json={"title": "Umbenannt", "status": "done"}, headers=alice).json()
    assert (changed["source_kind"], changed["source_id"]) == ("idea", IDEA_ID)


@pytest.mark.asyncio
async def test_task_read_nennt_die_idee():
    from backend import service
    from backend.tools.task_read import TOOL

    task = service.create_task("alice", title="Aus Idee")
    ohne = (await TOOL.execute({"task_id": task["id"]}, _ctx())).output["summary"]
    assert "Herkunft" not in ohne
    _set_source(task["id"], "idea", IDEA_ID)
    result = await TOOL.execute({"task_id": task["id"]}, _ctx())
    assert "Herkunft: Idee aaaa1111 (lesen mit idea_read)" in result.output["summary"]
    assert result.output["task"]["source_id"] == IDEA_ID


@pytest.mark.asyncio
async def test_task_read_zeigt_eine_unbekannte_herkunft_roh():
    from backend import service
    from backend.tools.task_read import TOOL

    task = service.create_task("alice", title="Aus etwas anderem")
    _set_source(task["id"], "ticket", "T-17")
    summary = (await TOOL.execute({"task_id": task["id"]}, _ctx())).output["summary"]
    assert "Herkunft: ticket T-17" in summary


def test_bestehende_tasks_ueberstehen_die_migration():
    """Stand 1.2.1 (Migration 001 und 002) mit Daten, danach 003: nichts geht verloren."""
    import sqlite3

    migrations = Path(__file__).resolve().parent.parent / "migrations"
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        for name in ("001_tasks.sql", "002_task_history.sql"):
            conn.executescript((migrations / name).read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO module_tasks (id, username, title, description, status) VALUES (?, ?, ?, ?, ?)",
            ("t-alt", "alice", "Vor der Migration", "bleibt stehen", "in_progress"),
        )
        conn.executescript((migrations / "003_task_source.sql").read_text(encoding="utf-8"))
        row = dict(conn.execute("SELECT * FROM module_tasks WHERE id = 't-alt'").fetchone())
    finally:
        conn.close()
    assert (row["title"], row["description"], row["status"]) == ("Vor der Migration", "bleibt stehen", "in_progress")
    assert row["source_kind"] is None and row["source_id"] is None
