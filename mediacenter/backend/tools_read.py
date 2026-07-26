from __future__ import annotations

from pydantic import ValidationError

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import job_service, service
from .models import SearchRequest
from .tool_support import failure, principal_for

_MEDIA = ["movie", "tv", "book", "audiobook", "audioplay", "music"]
_SEARCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "query": {"type": "string", "minLength": 2, "maxLength": 200},
        "media_type": {"type": "string", "enum": _MEDIA},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 25},
        "year": {"type": "integer", "minimum": 1800, "maximum": 2100},
        "season": {"type": "integer", "minimum": 0, "maximum": 999},
        "episode": {"type": "string", "minLength": 1, "maxLength": 16},
        "author": {"type": "string", "minLength": 1, "maxLength": 200},
        "artist": {"type": "string", "minLength": 1, "maxLength": 200},
        "album": {"type": "string", "minLength": 1, "maxLength": 200},
        "max_age_days": {"type": "integer", "minimum": 1, "maximum": 3650},
        "min_size_mb": {"type": "integer", "minimum": 0, "maximum": 1000000},
        "max_size_mb": {"type": "integer", "minimum": 0, "maximum": 1000000},
    },
    "required": ["query", "media_type"],
}
_EMPTY_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {}}


async def _search(args: dict, ctx: ToolContext) -> ToolResult:
    principal = principal_for(ctx)
    if principal is None:
        return ToolResult.fail("invalid_principal")
    try:
        request = SearchRequest.model_validate(args)
        if request.limit > 50:
            return ToolResult.fail("mediacenter_request_invalid")
        response = await service.search_indexer(
            principal["username"], request, owner_id=principal["user_id"]
        )
        return ToolResult.ok(response.model_dump(mode="json"))
    except ValidationError:
        return ToolResult.fail("mediacenter_request_invalid")
    except Exception as exc:
        return failure(exc)


async def _list(args: dict, ctx: ToolContext, mode: str) -> ToolResult:
    if args:
        return ToolResult.fail("mediacenter_request_invalid")
    principal = principal_for(ctx)
    if principal is None:
        return ToolResult.fail("invalid_principal")
    try:
        rows = await job_service.list_jobs(
            principal["username"], mode, limit=50, owner_id=principal["user_id"]
        )
        return ToolResult.ok({"count": len(rows), "jobs": rows})
    except Exception as exc:
        return failure(exc)


async def _queue(args: dict, ctx: ToolContext) -> ToolResult:
    return await _list(args, ctx, "queue")


async def _history(args: dict, ctx: ToolContext) -> ToolResult:
    return await _list(args, ctx, "history")


SEARCH_TOOL = Tool(
    name="mediacenter_search",
    description="Durchsucht Treasure Maps nach bereinigten Medien-Treffern. Lädt nichts herunter.",
    schema=_SEARCH_SCHEMA,
    execute=_search,
    category="data",
    prompt_hint="Nur zur Suche verwenden; abgelehnte Profile niemals umgehen.",
)
QUEUE_TOOL = Tool(
    name="mediacenter_queue",
    description="Zeigt nur eigene, über das Mediacenter gestartete aktive SABnzbd-Jobs.",
    schema=_EMPTY_SCHEMA,
    execute=_queue,
    category="data",
)
HISTORY_TOOL = Tool(
    name="mediacenter_history",
    description="Zeigt nur eigene Mediacenter-Downloads aus der SABnzbd-Historie.",
    schema=_EMPTY_SCHEMA,
    execute=_history,
    category="data",
)
