"""task_list — Tasks kompakt und seitenweise abfragen."""
from __future__ import annotations

import json
from typing import Any

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100
_PREVIEW_CHARS = 80
_OUTPUT_BUDGET_CHARS = 40_000
_COMPACT_FIELDS = ("id", "project_id", "title", "status", "priority", "created_at", "updated_at")

_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["open", "in_progress", "done", "cancelled"],
            "description": "Optional: nach Status filtern. Ohne Filter: alle Tasks.",
        },
        "project_id": {
            "type": "string",
            "description": "Optional: nur Tasks des angegebenen Projekts.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": _MAX_LIMIT,
            "default": _DEFAULT_LIMIT,
            "description": "Maximale Tasks dieser Seite (1–100, Standard 20).",
        },
        "offset": {
            "type": "integer",
            "minimum": 0,
            "default": 0,
            "description": "Anzahl zu überspringender Tasks (Standard 0).",
        },
    },
}


def _preview(description: str | None) -> str:
    return " ".join((description or "").split())[:_PREVIEW_CHARS]


def _compact(task: dict[str, Any]) -> dict[str, Any]:
    result = {field: task.get(field) for field in _COMPACT_FIELDS}
    result["description_preview"] = _preview(task.get("description"))
    return result


def _summary_line(task: dict[str, Any]) -> str:
    status_icon = {"open": "○", "in_progress": "◑", "done": "●", "cancelled": "✗"}.get(
        task["status"], "?"
    )
    prio_tag = {"high": "[!]", "medium": "", "low": "[~]"}.get(task["priority"], "")
    preview = _preview(task.get("description"))
    description = f" — {preview}" if preview else ""
    return f"{status_icon} [{task['id'][:8]}] {prio_tag}{task['title']}{description}"


def _page_output(
    tasks: list[dict[str, Any]],
    *,
    total: int,
    offset: int,
    limit: int,
    budget_limited: bool,
) -> dict[str, Any]:
    returned = len(tasks)
    has_more = offset + returned < total
    output: dict[str, Any] = {
        "count": total,
        "returned": returned,
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": offset + returned if has_more else None,
        "budget_limited": budget_limited,
        "tasks": [_compact(task) for task in tasks],
        "summary": "\n".join(_summary_line(task) for task in tasks),
        "detail_hint": "Vollständige Details mit task_read(task_id=<id>) laden.",
    }
    if total == 0:
        output["message"] = "Keine Tasks gefunden."
    elif returned == 0:
        output["message"] = "Keine Tasks auf dieser Seite."
    return output


def _page_args(args: dict[str, Any]) -> tuple[int, int] | None:
    limit = args.get("limit", _DEFAULT_LIMIT)
    offset = args.get("offset", 0)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= _MAX_LIMIT:
        return None
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        return None
    return limit, offset


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    page_args = _page_args(args)
    if page_args is None:
        return ToolResult.fail("Ungültige Pagination: limit muss 1–100, offset mindestens 0 sein.")
    limit, offset = page_args
    # Wie task_write: ctx.project_id als Standard-Filter, explizites Argument hat Vorrang (Core e51b17ee).
    filters = {"status": args.get("status"), "project_id": args.get("project_id") or ctx.project_id or None}

    total = service.count_tasks(username, **filters)
    requested_tasks = service.list_tasks(username, **filters, limit=limit, offset=offset)
    tasks = list(requested_tasks)
    output = _page_output(tasks, total=total, offset=offset, limit=limit, budget_limited=False)
    while tasks and len(json.dumps(output, ensure_ascii=False)) > _OUTPUT_BUDGET_CHARS:
        tasks.pop()
        output = _page_output(tasks, total=total, offset=offset, limit=limit, budget_limited=True)
    return ToolResult.ok(output)


TOOL = Tool(
    name="task_list",
    description=(
        "Listet persistente Tasks kompakt und seitenweise auf. "
        "Vollständige Details danach mit task_read laden."
    ),
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
)
