"""task_read — einzelnen Task per ID abrufen."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import service
from ._ids import resolve

_SCHEMA = {
    "type": "object",
    "properties": {
        "task_id": {
            "type": "string",
            "description": "ID des Tasks (vollständig oder die ersten 8 Zeichen).",
        },
        "history": {
            "type": "boolean",
            "description": "true: zusätzlich alle früheren Fassungen von Titel und Beschreibung liefern.",
        },
    },
    "required": ["task_id"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    username = ctx.user_id
    if not username:
        return ToolResult.fail("Kein User-Kontext verfügbar.")

    task, error = resolve(username, args.get("task_id"))
    if task is None:
        return ToolResult.fail(error)

    status_icon = {"open": "○", "in_progress": "◑", "done": "●", "cancelled": "✗"}.get(task["status"], "?")
    lines = [
        f"{status_icon} {task['title']}",
        f"ID:       {task['id']}",
        f"Status:   {task['status']}",
        f"Priorität: {task['priority']}",
    ]
    if task.get("description"):
        lines.append(f"Beschreibung: {task['description']}")
    if task.get("project_id"):
        lines.append(f"Projekt:  {task['project_id']}")
    lines.append(f"Erstellt: {task['created_at']}")
    lines.append(f"Geändert: {task['updated_at']}")

    versions = service.history(username, task["id"]) or []
    if versions:
        word = "Fassung" if len(versions) == 1 else "Fassungen"
        lines.append(f"Verlauf:  {len(versions)} frühere {word} (history=true zeigt sie)")
    result: dict = {"task": task}
    if args.get("history") and versions:
        result["history"] = versions
        for v in versions:
            lines.append(f"\n--- Fassung vom {v['changed_at']} ({v['source']}) ---\n{v['title']}\n{v['description']}")
    result["summary"] = "\n".join(lines)
    return ToolResult.ok(result)


TOOL = Tool(
    name="task_read",
    description=(
        "Liest einen einzelnen Task per ID (vollständig oder 8-Zeichen-Prefix). "
        "Nützlich wenn die ID aus einem vorherigen task_write bekannt ist."
    ),
    schema=_SCHEMA,
    execute=_execute,
    category="productivity",
)
