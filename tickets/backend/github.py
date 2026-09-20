"""Contracts and persistence helpers for GitHub Projects links.

Secrets are referenced by credential name only. GitHub tokens never enter these
models or the ticket database.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import Field

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .models import StrictModel, TicketCreate, TicketUpdate
from . import audit, permissions, service


class GitHubConnectionCreate(StrictModel):
    project_id: str = Field(min_length=1, max_length=128)
    owner: str = Field(min_length=1, max_length=39, pattern=r"^[A-Za-z0-9_.-]+$")
    repository: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    project_number: int | None = Field(default=None, ge=1)
    project_node_id: str | None = Field(default=None, max_length=128)
    credential_name: str = Field(default="project_git_token", min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    enabled: bool = True
    sync_mode: str = Field(default="read_only", pattern=r"^(read_only|push|bidirectional)$")


class GitHubSyncRequest(StrictModel):
    state: str = Field(default="open", pattern=r"^(open|closed|all)$")
    limit: int = Field(default=100, ge=1, le=500)


class GitHubConnectionUpdate(StrictModel):
    sync_mode: str = Field(pattern=r"^(read_only|push|bidirectional)$")


class GitHubIssueUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=20_000)
    state: str | None = Field(default=None, pattern=r"^(open|closed)$")


class GitHubProjectFieldUpdate(StrictModel):
    project_id: str = Field(min_length=1, max_length=128)
    item_id: str = Field(min_length=1, max_length=128)
    field_id: str = Field(min_length=1, max_length=128)
    option_id: str = Field(min_length=1, max_length=128)


class GitHubProjectItemMutation(StrictModel):
    project_id: str = Field(min_length=1, max_length=128)
    content_id: str | None = Field(default=None, max_length=128)
    item_id: str | None = Field(default=None, max_length=128)


class GitHubDiscoveryRequest(StrictModel):
    project_id: str = Field(min_length=1, max_length=128)
    credential_name: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9][a-z0-9_-]{0,49}$")
    owner: str | None = Field(default=None, max_length=39, pattern=r"^[A-Za-z0-9_.-]+$")


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
            return _row(conn.execute(
                "SELECT * FROM module_ticket_github_connections "
                "WHERE project_id=? AND owner=? AND repository=? AND project_number IS ?",
                (body.project_id, body.owner, body.repository, body.project_number),
            ).fetchone())  # type: ignore[return-value]
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


def list_linked_tickets(connection_id: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT t.*, l.issue_number, l.issue_url, l.sync_state, l.last_synced_at, l.last_error, "
            "l.remote_state, l.remote_labels_json, l.remote_assignees_json "
            "FROM module_ticket_github_links l JOIN module_tickets t ON t.id=l.ticket_id "
            "WHERE l.connection_id=? ORDER BY t.updated_at DESC",
            (connection_id,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["tags"] = json.loads(item.pop("tags_json", "[]"))
        result.append(item)
    return result


def update_connection(connection_id: str, sync_mode: str, principal: AuthPrincipal) -> dict | None:
    with db(immediate=True) as conn:
        row = conn.execute("SELECT * FROM module_ticket_github_connections WHERE id=?", (connection_id,)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE module_ticket_github_connections SET sync_mode=?, updated_at=? WHERE id=?", (sync_mode, _now(), connection_id))
        return _row(conn.execute("SELECT * FROM module_ticket_github_connections WHERE id=?", (connection_id,)).fetchone())


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


def sync_issue_snapshot(connection: dict, issue: dict, principal: AuthPrincipal) -> dict:
    """Create or update one local ticket while retaining the remote snapshot."""
    owner = connection["owner"]
    repository = connection["repository"]
    issue_number = int(issue["number"])
    title = str(issue.get("title") or f"GitHub Issue #{issue_number}")[:200]
    body = str(issue.get("body") or "")[:20_000]
    labels = [str(item.get("name")) for item in ((issue.get("labels") or {}).get("nodes") or []) if item.get("name")]
    assignees = [str(item.get("login")) for item in ((issue.get("assignees") or {}).get("nodes") or []) if item.get("login")]
    with db() as conn:
        existing = conn.execute(
            "SELECT l.*, t.title AS ticket_title, t.description AS ticket_description "
            "FROM module_ticket_github_links l JOIN module_tickets t ON t.id=l.ticket_id "
            "WHERE l.connection_id=? AND l.owner=? AND l.repository=? AND l.issue_number=?",
            (connection["id"], owner, repository, issue_number),
        ).fetchone()
    if existing is None:
        ticket = service.create_ticket(
            TicketCreate(title=title, description=body, category="github", tags=["github"], project_id=connection["project_id"]),
            principal,
            actor_kind="system",
            actor_id=principal.user_id,
        )
        link_id = str(uuid4())
        with db(immediate=True) as conn:
            conn.execute(
                "INSERT INTO module_ticket_github_links "
                "(id,ticket_id,connection_id,owner,repository,issue_number,issue_node_id,issue_url,created_by) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (link_id, ticket["id"], connection["id"], owner, repository, issue_number,
                 issue.get("id"), issue.get("url") or f"https://github.com/{owner}/{repository}/issues/{issue_number}", principal.user_id),
            )
        ticket_id = ticket["id"]
        created = True
    else:
        ticket_id = existing["ticket_id"]
        created = False
        with db() as conn:
            ticket_row = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
            if ticket_row is None or not permissions.can_update_ticket(conn, ticket_row, principal):
                raise ValueError("github_ticket_update_forbidden")
        if existing["ticket_title"] != title or existing["ticket_description"] != body:
            service.update_ticket(
                ticket_id,
                TicketUpdate(title=title, description=body),
                principal,
                actor_kind="system",
                actor_id=principal.user_id,
            )
    with db(immediate=True) as conn:
        conn.execute(
            "UPDATE module_ticket_github_links SET issue_node_id=?, issue_url=?, sync_state='linked', "
            "last_synced_at=?, last_error=NULL, remote_title=?, remote_body=?, remote_state=?, "
            "remote_labels_json=?, remote_assignees_json=?, remote_updated_at=?, updated_at=? WHERE ticket_id=?",
            (issue.get("id"), issue.get("url") or f"https://github.com/{owner}/{repository}/issues/{issue_number}",
             _now(), title, body, issue.get("state"), json.dumps(labels), json.dumps(assignees),
             issue.get("updatedAt"), _now(), ticket_id),
        )
        result = conn.execute("SELECT * FROM module_ticket_github_links WHERE ticket_id=?", (ticket_id,)).fetchone()
    return {"ticket": service.get_ticket(ticket_id), "link": _row(result), "created": created}


def redact_connection(connection: dict) -> dict:
    """Return frontend/tool-safe metadata; credential value is never present."""
    return {key: value for key, value in connection.items() if key != "credential_value"}



def validate_remote_link(body: GitHubLinkCreate) -> GitHubLinkCreate:
    """Validate the issue through the configured read-only provider before linking."""
    from . import github_provider
    with db() as conn:
        connection = conn.execute(
            "SELECT * FROM module_ticket_github_connections WHERE id=? AND enabled=1",
            (body.connection_id,),
        ).fetchone()
    if connection is None or connection["owner"] != body.owner or connection["repository"] != body.repository:
        raise ValueError("github_connection_not_found")
    try:
        issue = github_provider.get_issue(
            connection["created_by"], connection["credential_name"], body.owner, body.repository, body.issue_number, connection["project_id"]
        )
    except github_provider.GitHubProviderError as exc:
        raise ValueError(exc.code) from exc
    return body.model_copy(update={"issue_node_id": issue.get("id"), "issue_url": issue.get("url") or body.issue_url})

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
