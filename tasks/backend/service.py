"""Tasks-Modul — CRUD-Service."""
from __future__ import annotations

import uuid
from typing import Any

from hydrahive.db.connection import db

from . import _history

VALID_STATUSES = {"open", "in_progress", "done", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high"}
HISTORY_LIMIT = 200  # Verlaufseinträge pro Task (restored-Einträge zählen mit, werden aber nie entfernt)


def list_tasks(
    username: str,
    status: str | None = None,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM module_tasks WHERE username = ?"
    params: list[Any] = [username]
    if status:
        sql += " AND status = ?"
        params.append(status)
    if project_id:
        sql += " AND project_id = ?"
        params.append(project_id)
    sql += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, created_at ASC"
    with db() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def get_task(username: str, task_id: str) -> dict[str, Any] | None:
    with db() as c:
        row = c.execute(
            "SELECT * FROM module_tasks WHERE id = ? AND username = ?",
            (task_id, username),
        ).fetchone()
        return dict(row) if row else None


def create_task(
    username: str,
    title: str,
    description: str = "",
    priority: str = "medium",
    project_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    task_id = str(uuid.uuid4())
    with db() as c:
        c.execute(
            """
            INSERT INTO module_tasks (id, username, project_id, session_id, title, description, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, username, project_id, session_id, title, description, priority),
        )
    return get_task(username, task_id)  # type: ignore[return-value]


def update_task(
    username: str,
    task_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    note: str | None = None,
) -> dict[str, Any] | None:
    """Ändert einen Task. Ändern sich Titel oder Beschreibung, wird die alte
    Fassung vorher im Verlauf gesichert (Task df2f2eb2). `note` hängt einen
    datierten Absatz an (nach einem evtl. Ersetzen durch `description`)."""
    task = get_task(username, task_id)
    if not task:
        return None
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"Ungültiger Status: {status!r}")
    if priority is not None and priority not in VALID_PRIORITIES:
        raise ValueError(f"Ungültige Priorität: {priority!r}")
    new_title = task["title"] if title is None else title
    new_desc = task["description"] if description is None else description
    if note is not None and note.strip():
        new_desc = _history.append_note(new_desc, note)
    fields: dict[str, Any] = {}
    if new_title != task["title"]:
        fields["title"] = new_title
    if new_desc != task["description"]:
        fields["description"] = new_desc
    if status is not None:
        fields["status"] = status
    if priority is not None:
        fields["priority"] = priority
    if not fields:
        return task
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with db() as c:
        if "title" in fields or "description" in fields:
            _history.save_version(c, task, HISTORY_LIMIT)
        c.execute(
            f"UPDATE module_tasks SET {set_clause}, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')"
            " WHERE id = ? AND username = ?",
            [*fields.values(), task_id, username],
        )
    return get_task(username, task_id)


def history(username: str, task_id: str) -> list[dict[str, Any]] | None:
    """Frühere Fassungen, neueste zuerst. None, wenn der Task nicht dem User gehört."""
    if not get_task(username, task_id):
        return None
    with db() as c:
        return _history.list_for(c, task_id)


def history_counts(username: str) -> dict[str, int]:
    with db() as c:
        return _history.counts_for(c, username)


def add_restored(username: str, task_id: str, *, title: str, description: str, seen_at: str) -> bool:
    """Trägt eine aus dem Chat-Verlauf wiederhergestellte Fassung ein (idempotent, nur eigene Tasks)."""
    if not get_task(username, task_id):
        return False
    with db() as c:
        return _history.add_restored(c, task_id, title, description, seen_at)


def delete_task(username: str, task_id: str) -> bool:
    with db() as c:
        cur = c.execute(
            "DELETE FROM module_tasks WHERE id = ? AND username = ?",
            (task_id, username),
        )
        return cur.rowcount > 0
