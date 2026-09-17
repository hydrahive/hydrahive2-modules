"""Agent tools that create, comment on, update, or task-link tickets."""
from __future__ import annotations

from pydantic import ValidationError

from hydrahive.db.connection import db
from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import permissions, service
from ..models import TicketCommentCreate, TicketCreate, TicketUpdate
from ..task_link import TaskLinkCreate, create_linked_task
from .context import invalid_principal, invalid_request, principal_for, service_failure


def _schema(properties: dict, required: list[str] | None = None) -> dict:
    result = {"type": "object", "additionalProperties": False, "properties": properties}
    if required:
        result["required"] = required
    return result


_CREATE_SCHEMA = _schema(
    {
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "description": {"type": "string", "maxLength": 20000},
        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
        "category": {"type": "string", "maxLength": 80},
        "tags": {"type": "array", "maxItems": 20, "items": {"type": "string", "maxLength": 40}},
        "assigned_to": {"type": ["string", "null"], "maxLength": 128},
        "team_id": {"type": ["string", "null"], "maxLength": 64},
        "project_id": {"type": ["string", "null"], "maxLength": 128},
        "task_id": {"type": ["string", "null"], "maxLength": 128},
        "session_id": {"type": ["string", "null"], "maxLength": 128},
    },
    ["title"],
)
_COMMENT_SCHEMA = _schema(
    {"ticket_id": {"type": "string", "minLength": 1, "maxLength": 128},
     "body": {"type": "string", "minLength": 1, "maxLength": 20000}},
    ["ticket_id", "body"],
)
_UPDATE_SCHEMA = _schema(
    {"ticket_id": {"type": "string", "minLength": 1, "maxLength": 128},
     "title": {"type": "string", "maxLength": 200},
     "description": {"type": ["string", "null"], "maxLength": 20000},
     "status": {"type": "string", "enum": ["open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"]},
     "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
     "category": {"type": ["string", "null"], "maxLength": 80},
     "tags": {"type": ["array", "null"], "maxItems": 20},
     "assigned_to": {"type": ["string", "null"], "maxLength": 128},
     "team_id": {"type": ["string", "null"], "maxLength": 64},
     "project_id": {"type": ["string", "null"], "maxLength": 128},
     "task_id": {"type": ["string", "null"], "maxLength": 128},
     "session_id": {"type": ["string", "null"], "maxLength": 128}},
    ["ticket_id"],
)
_TASK_SCHEMA = _schema(
    {"ticket_id": {"type": "string", "minLength": 1, "maxLength": 128},
     "title": {"type": "string", "maxLength": 200},
     "description": {"type": "string", "maxLength": 20000},
     "priority": {"type": "string", "enum": ["low", "medium", "high"]}},
    ["ticket_id"],
)


async def _create(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    payload = dict(args)
    payload.setdefault("project_id", ctx.project_id)
    payload.setdefault("session_id", ctx.session_id)
    try:
        request = TicketCreate.model_validate(payload)
        ticket = service.create_ticket(request, principal, actor_kind="agent", actor_id=ctx.agent_id)
        return ToolResult.ok({"created": True, "ticket": ticket})
    except (ValidationError, TypeError):
        return invalid_request()
    except Exception as exc:
        return service_failure(exc)


async def _comment(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        ticket_id = args["ticket_id"]
        if not isinstance(ticket_id, str) or not 1 <= len(ticket_id) <= 128:
            return invalid_request()
        request = TicketCommentCreate.model_validate({"body": args.get("body")})
        result = service.add_comment(
            ticket_id, request.body, principal, actor_kind="agent", actor_id=ctx.agent_id
        )
        return ToolResult.ok({"created": True, "comment": result})
    except (ValidationError, KeyError, TypeError):
        return invalid_request()
    except Exception as exc:
        return service_failure(exc)


async def _update(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        ticket_id = args["ticket_id"]
        if not isinstance(ticket_id, str) or not 1 <= len(ticket_id) <= 128:
            return invalid_request()
        request = TicketUpdate.model_validate(
            {key: value for key, value in args.items() if key != "ticket_id"}
        )
    except (ValidationError, KeyError, TypeError):
        return invalid_request()
    with db() as conn:
        row = conn.execute("SELECT * FROM module_tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            return ToolResult.fail("ticket_not_found")
        if not permissions.can_update_ticket(conn, row, principal):
            return ToolResult.fail("ticket_update_forbidden")
    try:
        result = service.update_ticket(
            ticket_id, request, principal, actor_kind="agent", actor_id=ctx.agent_id
        )
        return ToolResult.ok({"updated": True, "ticket": result})
    except Exception as exc:
        return service_failure(exc)


async def _create_task(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return invalid_principal()
    try:
        request = TaskLinkCreate.model_validate(args)
        with db() as conn:
            row = conn.execute("SELECT * FROM module_tickets WHERE id=?", (request.ticket_id,)).fetchone()
            if row is None:
                return ToolResult.fail("ticket_not_found")
            if not permissions.can_update_ticket(conn, row, principal):
                return ToolResult.fail("ticket_update_forbidden")
        task = create_linked_task(
            request, principal, project_id=ctx.project_id, session_id=ctx.session_id,
            actor_id=ctx.agent_id,
        )
        return ToolResult.ok({"created": True, "task": task, "ticket_id": request.ticket_id})
    except ValidationError:
        return invalid_request()
    except Exception as exc:
        return service_failure(exc)


CREATE_TOOL = Tool("ticket_create", "Erstellt ein internes HydraHive-Ticket.", _CREATE_SCHEMA, _create, category="productivity")
COMMENT_TOOL = Tool("ticket_comment", "Fügt einem internen Ticket einen Kommentar hinzu.", _COMMENT_SCHEMA, _comment, category="productivity")
UPDATE_TOOL = Tool("ticket_update", "Ändert Status, Priorität oder Zuständigkeit eines Tickets.", _UPDATE_SCHEMA, _update, category="productivity")
CREATE_TASK_TOOL = Tool("ticket_create_task", "Erstellt eine verknüpfte HydraHive-Task aus einem Ticket.", _TASK_SCHEMA, _create_task, category="productivity")
