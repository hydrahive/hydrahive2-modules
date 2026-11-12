"""Anmerkungen an einer Idee: der Agent schreibt daneben, nie in den Text des Nutzers."""
from __future__ import annotations

from typing import Any

from hydrahive.db.connection import db

from .store import IdeaError, now

AUTHORS = ("agent", "system")
MAX_NOTE = 10_000

_IDEAS = "module_scratchpad_ideas"
_NOTES = "module_scratchpad_idea_notes"


def _owned(conn, username: str, idea_id: str) -> bool:
    return conn.execute(
        f"SELECT 1 FROM {_IDEAS} WHERE username = ? AND id = ?", (username, idea_id)
    ).fetchone() is not None


def add(username: str, idea_id: str, *, author: str, body: Any, agent_name: str | None = None) -> dict | None:
    """Anmerkung anhängen und die Idee als geändert markieren. ``None`` bei fremder Idee."""
    text = str(body or "").strip()
    if not text:
        raise IdeaError("note_required")
    if len(text) > MAX_NOTE:
        raise IdeaError("note_too_long")
    if author not in AUTHORS:
        raise IdeaError("invalid_author")
    with db(immediate=True) as conn:
        if not _owned(conn, username, idea_id):
            return None
        return insert(conn, idea_id, author=author, body=text, agent_name=agent_name, stamp=now())


def insert(conn, idea_id: str, *, author: str, body: str, stamp: str, agent_name: str | None = None) -> dict:
    """Anmerkung in einer laufenden Transaktion schreiben. Besitz und Grenzen prüft der Aufrufer."""
    cur = conn.execute(
        f"INSERT INTO {_NOTES} (idea_id, author, agent_name, body, created_at) VALUES (?, ?, ?, ?, ?)",
        (idea_id, author, (agent_name or None), body, stamp),
    )
    conn.execute(f"UPDATE {_IDEAS} SET updated_at = ? WHERE id = ?", (stamp, idea_id))
    return dict(conn.execute(f"SELECT * FROM {_NOTES} WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_for(username: str, idea_id: str) -> list[dict]:
    """Anmerkungen einer eigenen Idee, älteste zuerst."""
    with db() as conn:
        if not _owned(conn, username, idea_id):
            return []
        rows = conn.execute(
            f"SELECT id, idea_id, author, agent_name, body, created_at FROM {_NOTES} "
            "WHERE idea_id = ? ORDER BY created_at, id", (idea_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def remove(username: str, idea_id: str, note_id: int) -> bool:
    with db() as conn:
        if not _owned(conn, username, idea_id):
            return False
        cur = conn.execute(f"DELETE FROM {_NOTES} WHERE idea_id = ? AND id = ?", (idea_id, note_id))
        return cur.rowcount > 0
