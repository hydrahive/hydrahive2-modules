"""Verlauf der Task-Beschreibungen (Task df2f2eb2, SPEC-HISTORY.md).

Alle Funktionen arbeiten auf einer offenen Verbindung, damit Sichern und
Ändern in derselben Transaktion passieren.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def note_stamp() -> str:
    return datetime.now(timezone.utc).strftime("[%Y-%m-%d %H:%M]")


def append_note(description: str, note: str) -> str:
    entry = f"{note_stamp()} {note.strip()}"
    return f"{description}\n\n{entry}" if description else entry


def save_version(c: sqlite3.Connection, task: dict[str, Any], limit: int) -> None:
    c.execute(
        f"INSERT INTO module_tasks_history (task_id, title, description, changed_at, source) "
        f"VALUES (?, ?, ?, {_NOW}, 'update')",
        (task["id"], task["title"], task["description"]),
    )
    _trim(c, task["id"], limit)


def add_restored(c: sqlite3.Connection, task_id: str, title: str, description: str, seen_at: str) -> bool:
    exists = c.execute(
        "SELECT 1 FROM module_tasks_history WHERE task_id = ? AND description = ? AND source = 'restored'",
        (task_id, description),
    ).fetchone()
    if exists:
        return False
    c.execute(
        "INSERT INTO module_tasks_history (task_id, title, description, changed_at, source) "
        "VALUES (?, ?, ?, ?, 'restored')",
        (task_id, title, description, seen_at),
    )
    return True


def _trim(c: sqlite3.Connection, task_id: str, limit: int) -> None:
    """Hält den Verlauf bei `limit` Einträgen; entfernt nur die ältesten 'update'-Einträge."""
    total = c.execute("SELECT COUNT(*) FROM module_tasks_history WHERE task_id = ?", (task_id,)).fetchone()[0]
    excess = total - limit
    if excess <= 0:
        return
    c.execute(
        "DELETE FROM module_tasks_history WHERE id IN ("
        "  SELECT id FROM module_tasks_history WHERE task_id = ? AND source = 'update'"
        "  ORDER BY changed_at ASC, id ASC LIMIT ?)",
        (task_id, excess),
    )


def list_for(c: sqlite3.Connection, task_id: str) -> list[dict[str, Any]]:
    rows = c.execute(
        "SELECT title, description, changed_at, source FROM module_tasks_history "
        "WHERE task_id = ? ORDER BY changed_at DESC, id DESC",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def counts_for(c: sqlite3.Connection, username: str) -> dict[str, int]:
    rows = c.execute(
        "SELECT h.task_id, COUNT(*) FROM module_tasks_history h "
        "JOIN module_tasks t ON t.id = h.task_id WHERE t.username = ? GROUP BY h.task_id",
        (username,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}
