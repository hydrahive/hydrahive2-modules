"""Contracts and persistence helpers for GitHub Projects links.

Secrets are referenced by credential name only. GitHub tokens never enter these
models or the ticket database.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import Field

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .models import StrictModel
from . import audit, permissions


class GitHubConnectionCreate(StrictModel):
    project_id: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9_.-]+$")
    repository: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    project_number: int | None = Field(default=None, ge=1)
    project_node_id: str | None = Field(default=None, max_length=128)
    credential_name: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    enabled: bool = True
    sync_mode: str = Field(default="read_only", pattern=r"^(read_only|push|bidirectional)$")


class GitHubLinkCreate(StrictModel):
    ticket_id: str = Field(min_length=1, max_length=128)
    connection_id: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9_.-]+$")
    repository: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    issue_number: int = Field(gt=0)
    issue_node_id: str | None = Field(default=None, max_length=128)
    project_node_id: str | None = Field(default=None, max_length=128)
    project_item_id: str | None = Field(default=None, max_length=128)
    issue_url: str = Field(min_length=1, max_length=500, pattern=r"^https://github\.com/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row else None


def create_connection(body: GitHubConnectionCreate, principal: AuthPrincipal) -> dict:
    connection_id = str(uuid4())
    with db(immediate=True) as conn:
        duplicate = conn.execute(
            "SELECT 1 FROM module_ticket_github_connections "
            "WHERE project_id=? AND owner=? AND repository=? "
            "AND project_number IS ?",
            (body.project_id, body.owner, body.repository, body.project_number),
        ).fetchone()
        if duplicate is not None:
            raise ValueError("github_connection_exists")
        try:
            conn.execute(
                "INSERT INTO module_ticket_github_connections "
                "(id,project_id,owner,repository,project_number,project_node_id,credential_name,enabled,sync_mode,created_by) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (connection_id, body.project_id, body.owner, body.repository, body.project_number,
                 body.project_node_id, body.credential_name, int(body.enabled), body.sync_mode,
                 principal.user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("github_connection_exists") from exc
        return _row(conn.execute(
            "SELECT * FROM module_ticket_github_connections WHERE id=?", (connection_id,)
        ).fetchone())  # type: ignore[return-value]


def list_connections(project_id: str) -> list[dict]:
    with db() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM module_ticket_github_connections WHERE project_id=? ORDER BY created_at",
            (project_id,),
        ).fetchall()]


def create_link(body: GitHubLinkCreate, principal: AuthPrincipal) -> dict:
    link_id = str(uuid4())
    with db(immediate=True) as conn:
        if conn.execute("SELECT 1 FROM module_tickets WHERE id=?", (body.ticket_id,)).fetchone() is None:
            raise ValueError("ticket_not_found")
        if conn.execute(
            "SELECT 1 FROM module_ticket_github_connections WHERE id=? AND enabled=1",
            (body.connection_id,),
        ).fetchone() is None:
            raise ValueError("github_connection_not_found")
        try:
            conn.execute(
                "INSERT INTO module_ticket_github_links "
                "(id,ticket_id,connection_id,owner,repository,issue_number,issue_node_id,project_node_id,project_item_id,issue_url,created_by) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (link_id, body.ticket_id, body.connection_id, body.owner, body.repository,
                 body.issue_number, body.issue_node_id, body.project_node_id, body.project_item_id,
                 body.issue_url, principal.user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("github_link_exists") from exc
        return _row(conn.execute(
            "SELECT * FROM module_ticket_github_links WHERE id=?", (link_id,)
        ).fetchone())  # type: ignore[return-value]


def get_link(ticket_id: str) -> dict | None:
    with db() as conn:
        return _row(conn.execute(
            "SELECT * FROM module_ticket_github_links WHERE ticket_id=?", (ticket_id,)
        ).fetchone())


def redact_connection(connection: dict) -> dict:
    """Return frontend/tool-safe metadata; credential value is never present."""
    return {key: value for key, value in connection.items() if key != "credential_value"}


def link_ticket(body: GitHubLinkCreate, principal: AuthPrincipal, *, actor_id: str | None = None) -> dict:
    with db() as conn:
        ticket = conn.execute("SELECT * FROM module_tickets WHERE id=?", (body.ticket_id,)).fetchone()
        if ticket is None:
            raise ValueError("ticket_not_found")
        if not permissions.can_update_ticket(conn, ticket, principal):
            raise ValueError("ticket_update_forbidden")
        connection = conn.execute(
            "SELECT * FROM module_ticket_github_connections WHERE id=? AND enabled=1",
            (body.connection_id,),
        ).fetchone()
        if connection is None:
            raise ValueError("github_connection_not_found")
        if connection["owner"] != body.owner or connection["repository"] != body.repository:
            raise ValueError("github_repository_mismatch")
        if ticket["project_id"] and ticket["project_id"] != connection["project_id"]:
            raise ValueError("github_project_mismatch")
    result = create_link(body, principal)
    with db(immediate=True) as conn:
        audit.record_event(conn, body.ticket_id, actor_id or principal.user_id, "agent" if actor_id else "user", "github_linked", {
            "owner": body.owner, "repository": body.repository, "issue_number": body.issue_number,
        })
    return result


def unlink_ticket(ticket_id: str, principal: AuthPrincipal, *, actor_id: str | None = None) -> dict:
    with db(immediate=True) as conn:
        ticket = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
        if ticket is None:
            raise ValueError("ticket_not_found")
        if not permissions.can_update_ticket(conn, ticket, principal):
            raise ValueError("ticket_update_forbidden")
        row = conn.execute("SELECT * FROM module_ticket_github_links WHERE ticket_id=?", (ticket_id,)).fetchone()
        if row is None:
            raise ValueError("github_link_not_found")
        conn.execute("DELETE FROM module_ticket_github_links WHERE ticket_id=?", (ticket_id,))
        audit.record_event(conn, ticket_id, actor_id or principal.user_id, "agent" if actor_id else "user", "github_unlinked", {
            "owner": row["owner"], "repository": row["repository"], "issue_number": row["issue_number"],
        })
        return dict(row)
