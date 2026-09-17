"""Optional bridge from a ticket to the installed persistent Tasks module."""
from __future__ import annotations

import sqlite3
from uuid import uuid4

from pydantic import Field

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .audit import record_event
from .models import StrictModel
from .service import TicketServiceError


class TaskLinkCreate(StrictModel):
    ticket_id: str = Field(min_length=1, max_length=128)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")


def create_linked_task(
    request: TaskLinkCreate,
    principal: AuthPrincipal,
    *,
    project_id: str | None,
    session_id: str | None,
    actor_id: str,
) -> dict:
    task_id = str(uuid4())
    with db(immediate=True) as conn:
        ticket = conn.execute(
            "SELECT id,title,task_id FROM module_tickets WHERE id=?", (request.ticket_id,)
        ).fetchone()
        if ticket is None:
            raise TicketServiceError("ticket_not_found")
        if ticket["task_id"]:
            raise TicketServiceError("task_already_linked")
        try:
            conn.execute(
                "INSERT INTO module_tasks "
                "(id,username,project_id,session_id,title,description,priority) VALUES(?,?,?,?,?,?,?)",
                (
                    task_id, principal.username, project_id, session_id,
                    request.title or ticket["title"], request.description, request.priority,
                ),
            )
        except sqlite3.OperationalError as exc:
            raise TicketServiceError("task_module_unavailable") from exc
        conn.execute(
            "UPDATE module_tickets SET task_id=?,updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
            (task_id, request.ticket_id),
        )
        record_event(
            conn, request.ticket_id, actor_id, "agent", "task_created",
            {"task_id": task_id, "project_id": project_id, "session_id": session_id},
        )
        row = conn.execute("SELECT * FROM module_tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row)
