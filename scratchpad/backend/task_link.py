"""Aus einer Idee einen Task machen (Etappe 2).

Das Tasks-Modul ist ein eigenes Modul und muss nicht installiert sein. Wie das
Tickets-Modul (``tickets/backend/task_link.py``) schreibt diese Brücke direkt in
dessen Tabelle ``module_tasks``, aber nur mit dem eigenen Nutzernamen und nur,
wenn es die Tabelle gibt. Task, Verweis an der Idee, Status und Anmerkung
entstehen in einer Transaktion: scheitert ein Schritt, bleibt nichts zurück.
"""
from __future__ import annotations

import sqlite3
import uuid

from hydrahive.db.connection import db

from . import notes, render, store

TASKS_TABLE = "module_tasks"
_IDEAS = "module_scratchpad_ideas"
_PLANNED = "planned"


def _exists(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TASKS_TABLE,)
    ).fetchone() is not None


def installed() -> bool:
    """Gibt es die Tabelle des Tasks-Moduls?"""
    with db() as conn:
        return _exists(conn)


def _task(conn: sqlite3.Connection, username: str, task_id: str) -> sqlite3.Row | None:
    if not _exists(conn):
        return None
    return conn.execute(
        f"SELECT id, title, status FROM {TASKS_TABLE} WHERE id = ? AND username = ?", (task_id, username)
    ).fetchone()


def info(username: str, idea: dict) -> dict | None:
    """Verweis für Detailansicht und Agententext. ``None``, wenn die Idee keinen Task hat.

    Ein gelöschter Task, ein Task eines anderen Nutzers und ein fehlendes
    Tasks-Modul sehen gleich aus: ``missing``.
    """
    task_id = idea.get("task_id")
    if not task_id:
        return None
    with db() as conn:
        row = _task(conn, username, task_id)
    return {
        "id": task_id, "short_id": task_id[:8],
        "title": row["title"] if row else None, "status": row["status"] if row else None,
        "missing": row is None,
    }


def _description(idea: sqlite3.Row) -> str:
    head = f"Aus Idee {idea['id'][:8]}: {idea['title']}"
    body = (idea["body"] or "").strip()
    return f"{head}\n\n{body}" if body else head


def create(username: str, idea_id: str) -> dict | None:
    """Task zur Idee anlegen und verknüpfen. ``None`` bei fremder oder unbekannter Idee."""
    task_id, stamp = str(uuid.uuid4()), store.now()
    with db(immediate=True) as conn:
        idea = conn.execute(f"SELECT * FROM {_IDEAS} WHERE username = ? AND id = ?", (username, idea_id)).fetchone()
        if idea is None:
            return None
        if not _exists(conn):
            raise store.IdeaError("tasks_not_installed")
        # Ein Verweis auf einen gelöschten Task sperrt nicht: dann darf ein neuer entstehen.
        if idea["task_id"] and _task(conn, username, idea["task_id"]) is not None:
            raise store.IdeaError("task_already_linked")
        conn.execute(
            f"INSERT INTO {TASKS_TABLE} (id, username, project_id, session_id, title, description, priority) "
            "VALUES (?, ?, ?, NULL, ?, ?, 'medium')",
            (task_id, username, idea["project_id"], idea["title"], _description(idea)),
        )
        conn.execute(
            f"UPDATE {_IDEAS} SET task_id = ?, status = ?, updated_at = ? WHERE username = ? AND id = ?",
            (task_id, _PLANNED, stamp, username, idea_id),
        )
        line = f"Task angelegt: {task_id[:8]}"
        if idea["status"] != _PLANNED:
            line += f". Status: {render.status_label(idea['status'])} → {render.status_label(_PLANNED)}"
        notes.insert(conn, idea_id, author="system", body=line, stamp=stamp)
    return store.get(username, idea_id)
