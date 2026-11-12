"""Aus einer Idee einen Task machen (Etappe 2).

Das Tasks-Modul ist ein eigenes Modul und muss nicht installiert sein. Wie das
Tickets-Modul (``tickets/backend/task_link.py``) schreibt diese Brücke direkt in
dessen Tabelle ``module_tasks``, aber nur mit dem eigenen Nutzernamen und nur,
wenn es die Tabelle gibt. Task, Verweis an der Idee, Status und Anmerkung
entstehen in einer Transaktion: scheitert ein Schritt, bleibt nichts zurück.

Ab Tasks 1.3.0 trägt der Task die Idee als Herkunft (``source_kind``,
``source_id``). Ein älteres Tasks-Modul ohne diese Spalten bekommt den Task
wie bisher, nur ohne Rückverweis.
"""
from __future__ import annotations

import sqlite3
import uuid

from hydrahive.db.connection import db

from . import notes, render, store

TASKS_TABLE = "module_tasks"
_IDEAS = "module_scratchpad_ideas"
_PLANNED = "planned"
SOURCE_KIND = "idea"
_SOURCE_COLUMNS = {"source_kind", "source_id"}


def _exists(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TASKS_TABLE,)
    ).fetchone() is not None


def _has_source(conn: sqlite3.Connection) -> bool:
    """Kennt das installierte Tasks-Modul die Spalten für die Herkunft?"""
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({TASKS_TABLE})")}
    return _SOURCE_COLUMNS <= columns


def _insert_task(conn: sqlite3.Connection, task_id: str, username: str, idea: sqlite3.Row) -> None:
    values = {
        "id": task_id, "username": username, "project_id": idea["project_id"], "session_id": None,
        "title": idea["title"], "description": _description(idea), "priority": "medium",
    }
    if _has_source(conn):
        values.update(source_kind=SOURCE_KIND, source_id=idea["id"])
    columns, marks = ", ".join(values), ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO {TASKS_TABLE} ({columns}) VALUES ({marks})", list(values.values()))


def backfill(username: str) -> int:
    """Herkunft bei Tasks nachtragen, die vor Tasks 1.3.0 aus einer Idee entstanden sind.

    Nur eigene Tasks, nur wenn dort noch keine Herkunft steht. Titel, Beschreibung
    und Änderungszeit des Tasks bleiben unberührt. Liefert die Zahl der Nachträge.
    """
    with db() as conn:
        if not _exists(conn) or not _has_source(conn):
            return 0
        rows = conn.execute(
            f"SELECT i.id AS idea_id, i.task_id FROM {_IDEAS} i "
            f"JOIN {TASKS_TABLE} t ON t.id = i.task_id AND t.username = i.username "
            "WHERE i.username = ? AND t.source_kind IS NULL AND t.source_id IS NULL",
            (username,),
        ).fetchall()
        # Geschrieben wird nur, wenn es etwas nachzutragen gibt: der Normalfall bleibt ein reiner Lesezugriff.
        for row in rows:
            conn.execute(
                f"UPDATE {TASKS_TABLE} SET source_kind = ?, source_id = ? "
                "WHERE id = ? AND username = ? AND source_kind IS NULL AND source_id IS NULL",
                (SOURCE_KIND, row["idea_id"], row["task_id"], username),
            )
    return len(rows)


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
        _insert_task(conn, task_id, username, idea)
        conn.execute(
            f"UPDATE {_IDEAS} SET task_id = ?, status = ?, updated_at = ? WHERE username = ? AND id = ?",
            (task_id, _PLANNED, stamp, username, idea_id),
        )
        line = f"Task angelegt: {task_id[:8]}"
        if idea["status"] != _PLANNED:
            line += f". Status: {render.status_label(idea['status'])} → {render.status_label(_PLANNED)}"
        notes.insert(conn, idea_id, author="system", body=line, stamp=stamp)
    return store.get(username, idea_id)
