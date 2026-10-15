"""Agenten-Werkzeug display_message: kurze Nachricht auf dem Gehäuse-Display einblenden (standardmäßig aus)."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult
from renderer import inbox

from . import notify

_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "description": "Kurzer Text (max. 280 Zeichen, keine Links/Bilder)."},
        "title": {"type": "string", "description": "Optional: Überschrift (max. 60 Zeichen)."},
        "kind": {"type": "string", "enum": list(inbox.KINDS), "description": "Stil: info, success, warning, error. Default info."},
        "seconds": {"type": "integer", "minimum": 3, "maximum": 600, "description": "Anzeigedauer. Default 15 (Fehler 600)."},
    },
    "required": ["text"],
}


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    try:
        m = inbox.post(notify.data_dir(), notify.safe_text(args.get("text", ""), ctx.user_id, ctx.agent_id),
                       kind=str(args.get("kind") or "info"),
                       title=notify.safe_text(args.get("title", ""), ctx.user_id, ctx.agent_id),
                       seconds=args.get("seconds"), source=f"agent:{ctx.agent_id}")
    except (inbox.InboxError, TypeError, ValueError) as e:
        return ToolResult.fail(str(e))
    return ToolResult.ok(f"Auf der Vitrine eingeblendet ({m['kind']}, {int(m['expires'] - m['created'])} s).")


DISPLAY_TOOL = Tool(
    name="display_message",
    description="Blendet eine kurze Nachricht auf dem Gehäuse-Display (Vitrine) im Wohnzimmer ein. "
                "Nur für kurze Hinweise an Menschen im Raum, z. B. 'Backup fertig'.",
    schema=_SCHEMA,
    execute=_execute,
)
