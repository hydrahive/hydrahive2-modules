"""Ideen-Speicher: jede Idee gehört dem Nutzer, der sie anlegt.

Alle Abfragen filtern auf ``username``. Fremde Ideen sind unsichtbar und
unveränderbar. Das Projekt ist nur eine Zuordnung, keine Freigabe. Ob der
Nutzer auf das Projekt zugreifen darf, prüft ``access.py`` vor dem Schreiben.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from hydrahive.db.connection import db

STATUSES = ("new", "review", "planned", "parked", "done", "dropped")
OPEN_STATUSES = ("new", "review", "planned")
ORIGINS = ("user", "agent")
NO_PROJECT = "none"  # Filterwert für „ohne Projekt“
MAX_IDEAS = 2000
MAX_TITLE = 200
MAX_BODY = 50_000
PREVIEW_CHARS = 160
UNSET: Any = object()

_TABLE = "module_scratchpad_ideas"
_NOTES = "module_scratchpad_idea_notes"
_LIST_COLUMNS = (
    "i.id, i.project_id, i.title, i.status, i.origin, i.task_id, i.board_id, i.created_at, "
    f"i.updated_at, substr(i.body, 1, 600) AS body_head, "
    f"(SELECT COUNT(*) FROM {_NOTES} n WHERE n.idea_id = i.id) AS note_count"
)


class IdeaError(ValueError):
    """Benannter Fehler; ``code`` geht unverändert an Route und Werkzeug."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def now() -> str:
    """UTC mit Mikrosekunden, damit „neueste Änderung zuerst“ eindeutig sortiert."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def clean_title(title: Any) -> str:
    text = " ".join(str(title or "").split())
    if not text:
        raise IdeaError("title_required")
    if len(text) > MAX_TITLE:
        raise IdeaError("title_too_long")
    return text


def check_body(body: Any) -> str:
    text = str(body or "")
    if len(text) > MAX_BODY:
        raise IdeaError("body_too_long")
    return text


def _where(username: str, project: str | None, statuses: tuple[str, ...] | None) -> tuple[str, list]:
    clauses, args = ["i.username = ?"], [username]
    if project == NO_PROJECT:
        clauses.append("i.project_id IS NULL")
    elif project:
        clauses.append("i.project_id = ?")
        args.append(project)
    if statuses:
        clauses.append(f"i.status IN ({','.join('?' * len(statuses))})")
        args.extend(statuses)
    return " AND ".join(clauses), args


def _list_row(row) -> dict:
    item = dict(row)
    item["body_preview"] = " ".join(item.pop("body_head").split())[:PREVIEW_CHARS]
    return item


def list_ideas(username: str, *, project: str | None = None, statuses: tuple[str, ...] | None = None,
               limit: int | None = None, offset: int = 0) -> list[dict]:
    """Ideen des Nutzers ohne volle Beschreibung, neueste Änderung zuerst."""
    where, args = _where(username, project, statuses)
    sql = f"SELECT {_LIST_COLUMNS} FROM {_TABLE} i WHERE {where} ORDER BY i.updated_at DESC, i.id"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        args += [limit, offset]
    with db() as conn:
        return [_list_row(r) for r in conn.execute(sql, args).fetchall()]


def count(username: str, *, project: str | None = None, statuses: tuple[str, ...] | None = None) -> int:
    where, args = _where(username, project, statuses)
    with db() as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {_TABLE} i WHERE {where}", args).fetchone()[0])


def count_by_status(username: str, *, project: str | None = None) -> dict[str, int]:
    where, args = _where(username, project, None)
    counts = dict.fromkeys(STATUSES, 0)
    with db() as conn:
        rows = conn.execute(
            f"SELECT i.status, COUNT(*) FROM {_TABLE} i WHERE {where} GROUP BY i.status", args
        ).fetchall()
    for status, number in rows:
        if status in counts:
            counts[status] = int(number)
    return counts


def get(username: str, idea_id: str) -> dict | None:
    with db() as conn:
        row = conn.execute(
            f"SELECT * FROM {_TABLE} WHERE username = ? AND id = ?", (username, idea_id)
        ).fetchone()
    return dict(row) if row else None


def ids_with_prefix(username: str, prefix: str, limit: int = 6) -> list[dict]:
    """Treffer für eine Kurz-ID (Anfang der ID), für die Werkzeuge."""
    escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, title FROM {_TABLE} WHERE username = ? AND id LIKE ? ESCAPE '\\' "
            "ORDER BY updated_at DESC LIMIT ?", (username, escaped + "%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def create(username: str, *, title: Any, body: Any = "", project_id: str | None = None,
           origin: str = "user", idea_id: str | None = None) -> dict:
    title, body = clean_title(title), check_body(body)
    if origin not in ORIGINS:
        raise IdeaError("invalid_origin")
    new_id, stamp = idea_id or str(uuid.uuid4()), now()
    with db(immediate=True) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM {_TABLE} WHERE username = ?", (username,)).fetchone()[0]
        if total >= MAX_IDEAS:
            raise IdeaError("ideas_full")
        conn.execute(
            f"INSERT INTO {_TABLE} (id, username, project_id, title, body, status, origin, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, 'new', ?, ?, ?)",
            (new_id, username, project_id or None, title, body, origin, stamp, stamp),
        )
    return get(username, new_id)  # type: ignore[return-value]


def update(username: str, idea_id: str, *, title: Any = UNSET, body: Any = UNSET, status: Any = UNSET,
           project_id: Any = UNSET, task_id: Any = UNSET, board_id: Any = UNSET) -> dict | None:
    """Nur übergebene Felder ändern. ``None`` bei fremder oder unbekannter Idee."""
    fields: dict[str, Any] = {}
    if title is not UNSET:
        fields["title"] = clean_title(title)
    if body is not UNSET:
        fields["body"] = check_body(body)
    if status is not UNSET:
        if status not in STATUSES:
            raise IdeaError("invalid_status")
        fields["status"] = status
    if project_id is not UNSET:
        fields["project_id"] = project_id or None
    if task_id is not UNSET:
        fields["task_id"] = task_id or None
    if board_id is not UNSET:
        fields["board_id"] = board_id
    if not fields:
        return get(username, idea_id)
    fields["updated_at"] = now()
    assignments = ", ".join(f"{name} = ?" for name in fields)
    with db() as conn:
        cur = conn.execute(
            f"UPDATE {_TABLE} SET {assignments} WHERE username = ? AND id = ?",
            (*fields.values(), username, idea_id),
        )
        if cur.rowcount == 0:
            return None
    return get(username, idea_id)


def delete(username: str, idea_id: str) -> bool:
    """Idee samt Anmerkungen entfernen. Verknüpfter Task und Board bleiben bestehen."""
    with db() as conn:
        cur = conn.execute(f"DELETE FROM {_TABLE} WHERE username = ? AND id = ?", (username, idea_id))
        return cur.rowcount > 0
