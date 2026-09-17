"""Read-only agent tools for internal ticket search and detail views."""
from __future__ import annotations

from pydantic import ValidationError

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import attachments, service
from ..models import TicketListQuery
from .context import invalid_principal, invalid_request, principal_for

_LIST_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"]},
        "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
        "team_id": {"type": "string", "maxLength": 64},
        "assigned_to": {"type": "string", "maxLength": 128},
        "project_id": {"type": "string", "maxLength": 128},
        "query": {"type": "string", "maxLength": 200},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "offset": {"type": "integer", "minimum": 0},
    },
}
_READ_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["ticket_id"],
    "properties": {"ticket_id": {"type": "string", "minLength": 1, "maxLength": 128}},
}


def _compact(ticket: dict) -> dict:
    result = dict(ticket)
    result["description"] = result.get("description", "")[:1_000]
    return result


async def _list(args: dict, ctx: ToolContext) -> ToolResult:
    if principal_for(ctx) is None:
        return invalid_principal()
    try:
        query = TicketListQuery.model_validate(args)
    except ValidationError:
        return invalid_request()
    rows = service.list_tickets(
        status=query.status, priority=query.priority, team_id=query.team_id,
        assigned_to=query.assigned_to, project_id=query.project_id, query=query.query,
        limit=query.limit, offset=query.offset,
    )
    return ToolResult.ok({"count": len(rows), "tickets": [_compact(row) for row in rows]})


async def _read(args: dict, ctx: ToolContext) -> ToolResult:
    if principal_for(ctx) is None:
        return invalid_principal()
    try:
        ticket_id = args["ticket_id"]
        if not isinstance(ticket_id, str) or not 1 <= len(ticket_id) <= 128 or set(args) != {"ticket_id"}:
            return invalid_request()
    except (KeyError, TypeError):
        return invalid_request()
    ticket = service.get_ticket(ticket_id)
    if ticket is None:
        return ToolResult.fail("ticket_not_found")
    result = _compact(ticket)
    result["comments"] = service.list_comments(ticket_id)
    result["events"] = service.list_events(ticket_id)
    result["attachments"] = [
        {key: value for key, value in item.items() if key not in {"storage_key", "sha256", "uploaded_by"}}
        for item in attachments.list_attachments(ticket_id)
    ]
    return ToolResult.ok(result)


LIST_TOOL = Tool(
    name="ticket_list",
    description="Sucht und filtert interne HydraHive-Tickets.",
    schema=_LIST_SCHEMA, execute=_list, category="productivity",
)
READ_TOOL = Tool(
    name="ticket_read",
    description="Liest ein internes Ticket mit Verlauf und sicheren Anhangsmetadaten.",
    schema=_READ_SCHEMA, execute=_read, category="productivity",
)
