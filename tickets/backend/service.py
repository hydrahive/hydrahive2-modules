"""Transactional ticket domain operations.

Authorization stays at the route/tool boundary; this service keeps all writes
atomic and records the append-only event history for every mutation.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .audit import list_events, record_event
from .models import TicketCreate, TicketUpdate
from .notifications import notify_ticket

_ALLOWED_TRANSITIONS = {
    "open": {"triaged", "in_progress", "cancelled"},
    "triaged": {"in_progress", "waiting", "cancelled"},
    "in_progress": {"waiting", "resolved", "cancelled"},
    "waiting": {"in_progress", "resolved", "cancelled"},
    "resolved": {"closed", "in_progress"},
    "closed": {"open"},
    "cancelled": {"open"},
}


class TicketServiceError(ValueError):
    """A user-correctable domain error with a stable error code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ticket(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    result["tags"] = json.loads(result.pop("tags_json", "[]"))
    return result


def create_ticket(
    body: TicketCreate,
    principal: AuthPrincipal,
    *,
    actor_kind: str = "user",
    actor_id: str | None = None,
) -> dict:
    ticket_id = str(uuid4())
    event_actor = actor_id or principal.user_id
    values = (
        ticket_id, body.title, body.description, body.priority, body.category,
        json.dumps(body.tags, ensure_ascii=False), principal.user_id, body.assigned_to,
        body.team_id, body.project_id, body.task_id, body.session_id,
    )
    with db(immediate=True) as conn:
        try:
            conn.execute(
                "INSERT INTO module_tickets "
                "(id,title,description,priority,category,tags_json,created_by,assigned_to,"
                "team_id,project_id,task_id,session_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                values,
            )
        except sqlite3.IntegrityError as exc:
            raise TicketServiceError("invalid_ticket_reference") from exc
        record_event(conn, ticket_id, event_actor, actor_kind, "ticket_created", {
            "priority": body.priority,
            "team_id": body.team_id,
            "assigned_to": body.assigned_to,
        })
        notify_ticket(conn, ticket_id, principal.user_id, "ticket_created")
        row = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
    return _ticket(row)  # type: ignore[return-value]


def get_ticket(ticket_id: str) -> dict | None:
    with db() as conn:
        return _ticket(conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone())


def list_tickets(
    *, status: str | None = None, priority: str | None = None, team_id: str | None = None,
    assigned_to: str | None = None, project_id: str | None = None, query: str | None = None,
    limit: int = 50, offset: int = 0,
) -> list[dict]:
    clauses: list[str] = []
    args: list[Any] = []
    for column, value in (("status", status), ("priority", priority), ("team_id", team_id),
                          ("assigned_to", assigned_to), ("project_id", project_id)):
        if value is not None:
            clauses.append(f"{column}=?")
            args.append(value)
    if query:
        clauses.append("(title LIKE ? OR description LIKE ?)")
        args.extend((f"%{query}%", f"%{query}%"))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    args.extend((limit, offset))
    with db() as conn:
        rows = conn.execute(
            f"SELECT * FROM module_tickets {where} ORDER BY updated_at DESC, number DESC LIMIT ? OFFSET ?",
            args,
        ).fetchall()
    return [_ticket(row) for row in rows]  # type: ignore[misc]


def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    principal: AuthPrincipal,
    *,
    actor_kind: str = "user",
    actor_id: str | None = None,
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    event_actor = actor_id or principal.user_id
    with db(immediate=True) as conn:
        before = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
        if before is None:
            raise TicketServiceError("ticket_not_found")
        if not changes:
            return _ticket(before)  # type: ignore[return-value]
        if "status" in changes and changes["status"] != before["status"]:
            if changes["status"] not in _ALLOWED_TRANSITIONS[before["status"]]:
                raise TicketServiceError("invalid_status_transition")
        assignments: list[str] = []
        args: list[Any] = []
        for field in ("title", "description", "status", "priority", "category", "assigned_to",
                      "team_id", "project_id", "task_id", "session_id"):
            if field in changes:
                assignments.append(f"{field}=?")
                args.append(changes[field])
        if "tags" in changes:
            assignments.append("tags_json=?")
            args.append(json.dumps(changes["tags"], ensure_ascii=False))
        status_value = changes.get("status")
        if status_value == "resolved":
            assignments.append("resolved_at=COALESCE(resolved_at,?)")
            args.append(_now())
        elif status_value == "in_progress" and before["status"] == "resolved":
            assignments.append("resolved_at=NULL")
        if status_value == "closed":
            assignments.append("closed_at=COALESCE(closed_at,?)")
            args.append(_now())
        elif status_value == "open" and before["status"] == "closed":
            assignments.append("closed_at=NULL")
        assignments.append("updated_at=?")
        args.extend((_now(), ticket_id))
        try:
            conn.execute(f"UPDATE module_tickets SET {','.join(assignments)} WHERE id=?", args)
        except sqlite3.IntegrityError as exc:
            raise TicketServiceError("invalid_ticket_reference") from exc
        record_event(conn, ticket_id, event_actor, actor_kind, "ticket_updated", changes)
        notify_ticket(conn, ticket_id, principal.user_id, "ticket_updated")
        after = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
    return _ticket(after)  # type: ignore[return-value]


def add_comment(
    ticket_id: str,
    body: str,
    principal: AuthPrincipal,
    *,
    actor_kind: str = "user",
    actor_id: str | None = None,
) -> dict:
    comment_id = str(uuid4())
    event_actor = actor_id or principal.user_id
    with db(immediate=True) as conn:
        if conn.execute("SELECT 1 FROM module_tickets WHERE id=?", (ticket_id,)).fetchone() is None:
            raise TicketServiceError("ticket_not_found")
        conn.execute(
            "INSERT INTO module_ticket_comments(id,ticket_id,author_id,author_kind,body) VALUES(?,?,?,?,?)",
            (comment_id, ticket_id, event_actor, actor_kind, body),
        )
        conn.execute("UPDATE module_tickets SET updated_at=? WHERE id=?", (_now(), ticket_id))
        record_event(conn, ticket_id, event_actor, actor_kind, "comment_added", {"comment_id": comment_id})
        notify_ticket(conn, ticket_id, principal.user_id, "comment_added")
        row = conn.execute("SELECT * FROM module_ticket_comments WHERE id=?", (comment_id,)).fetchone()
    return dict(row)


def list_comments(ticket_id: str, *, limit: int = 100, offset: int = 0) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM module_ticket_comments WHERE ticket_id=? "
            "ORDER BY rowid ASC LIMIT ? OFFSET ?",
            (ticket_id, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]

