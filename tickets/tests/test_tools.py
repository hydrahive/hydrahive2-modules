from __future__ import annotations

from pathlib import Path

import pytest

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db
from hydrahive.tools.base import ToolContext

from backend.models import TicketCreate
from backend.service import create_ticket, get_ticket, list_events
from backend.tools.read import LIST_TOOL, READ_TOOL
from backend.tools.write import COMMENT_TOOL, CREATE_TASK_TOOL, CREATE_TOOL, UPDATE_TOOL


def ctx(user: str = "member") -> ToolContext:
    return ToolContext(session_id="session-1", agent_id="agent-1", user_id=user, workspace=Path("."), project_id="project-1")


def principal(user_id: str = "user-member") -> AuthPrincipal:
    return AuthPrincipal(user_id, "member", "user")


def make_ticket() -> dict:
    return create_ticket(TicketCreate(title="Agenten-Vorgang"), principal())


@pytest.mark.asyncio
async def test_read_tools_return_compact_ticket_data(ticket_db):
    ticket = make_ticket()
    listed = await LIST_TOOL.execute({"status": "open"}, ctx())
    read = await READ_TOOL.execute({"ticket_id": ticket["id"]}, ctx())

    assert listed.success is True
    assert listed.output["count"] == 1
    assert read.success is True
    assert read.output["id"] == ticket["id"]
    assert read.output["attachments"] == []


@pytest.mark.asyncio
async def test_write_tools_use_agent_audit_identity(ticket_db):
    ticket = make_ticket()
    comment = await COMMENT_TOOL.execute(
        {"ticket_id": ticket["id"], "body": "Agent hat geprüft."}, ctx()
    )
    update = await UPDATE_TOOL.execute(
        {"ticket_id": ticket["id"], "priority": "high"}, ctx()
    )

    assert comment.success is True
    assert update.success is True
    assert comment.output["comment"]["author_id"] == "agent-1"
    assert comment.output["comment"]["author_kind"] == "agent"
    assert list_events(ticket["id"])[-1]["actor_id"] == "agent-1"


@pytest.mark.asyncio
async def test_create_tool_inherits_project_and_session_context(ticket_db):
    result = await CREATE_TOOL.execute({"title": "Kontext-Ticket"}, ctx())
    ticket = result.output["ticket"]

    assert result.success is True
    assert ticket["project_id"] == "project-1"
    assert ticket["session_id"] == "session-1"
    assert ticket["created_by"] == "user-member"


@pytest.mark.asyncio
async def test_tools_reject_invalid_context_and_foreign_update(ticket_db):
    invalid = await LIST_TOOL.execute({}, ctx("unknown-user"))
    ticket = create_ticket(TicketCreate(title="Fremd"), AuthPrincipal("user-other", "other", "user"))
    denied = await UPDATE_TOOL.execute(
        {"ticket_id": ticket["id"], "title": "Darf ich nicht"}, ctx()
    )

    assert invalid.success is False
    assert invalid.error == "invalid_principal"
    assert denied.success is False
    assert denied.error == "ticket_update_forbidden"


@pytest.mark.asyncio
async def test_create_task_tool_links_existing_tasks_module(ticket_db):
    with db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS module_tasks ("
            "id TEXT PRIMARY KEY, username TEXT NOT NULL, project_id TEXT, session_id TEXT, "
            "title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', priority TEXT NOT NULL DEFAULT 'medium', "
            "status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL DEFAULT 'now', updated_at TEXT NOT NULL DEFAULT 'now')"
        )
        conn.execute("DELETE FROM module_tasks")
    ticket = make_ticket()
    result = await CREATE_TASK_TOOL.execute(
        {"ticket_id": ticket["id"], "title": "Konkrete Umsetzung", "priority": "high"}, ctx()
    )
    linked = get_ticket(ticket["id"])

    assert result.success is True
    assert result.output["task"]["title"] == "Konkrete Umsetzung"
    assert linked["task_id"] == result.output["task"]["id"]
    assert list_events(ticket["id"])[-1]["event_type"] == "task_created"
