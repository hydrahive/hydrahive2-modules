"""task_delete — Task endgültig löschen."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service
from ._ids import resolve

_SCHEMA = {
    "type": "object",
    "required": ["task_id"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "ID des Tasks (vollständig oder 8-Zeichen-Prefix).",
        },
    },
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    task, error = resolve(username, args.get("task_id"))
    if task is None:
        return ToolResult.fail(error)
    task_id = task["id"]

    if not service.delete_task(username, task_id):
        return ToolResult.fail(f"Task '{task_id}' nicht gefunden.")

    return ToolResult.ok({"deleted": True, "task_id": task_id})


TOOL = Tool(
    name="task_delete",
    description="Löscht einen Task endgültig. Verwende dies wenn ein Task nicht mehr gebraucht wird.",
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
)
