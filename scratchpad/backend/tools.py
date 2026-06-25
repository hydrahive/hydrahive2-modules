from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import service
from .service import ScratchpadTooLarge

_READ_DESCRIPTION = (
    "Liest das Scratchpad des Users: die handgeschriebenen Ideen des Users plus deine "
    "eigenen Agent-Notizen. Nutze es, wenn die Aufgabe auf notierte Ideen Bezug nimmt."
)
_READ_SCHEMA = {"type": "object", "properties": {}, "required": []}
_PROMPT_HINT = (
    "\n\nScratchpad: Der User hinterlegt hier Ideen und Notizen. Lies sie mit "
    "`read_scratchpad`, wenn die Aufgabe darauf Bezug nimmt. Eigene Notizen "
    "schreibst du mit `write_scratchpad` — nur in deinen Bereich; der Bereich des Users ist tabu."
)

_WRITE_DESCRIPTION = (
    "Schreibt in DEINE Agent-Notiz-Zone des Scratchpads (ersetzt sie komplett). "
    "Der eigene Bereich des Users ist tabu und kann hierüber nicht verändert werden. "
    "Lies vorher mit read_scratchpad, damit du deine bestehenden Notizen nicht verlierst."
)
_WRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string", "description": "Vollständiger neuer Inhalt deiner Agent-Zone (Markdown)."},
    },
    "required": ["content"],
}


async def _read(args: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult.ok(service.get_combined(ctx.user_id))


async def _write(args: dict, ctx: ToolContext) -> ToolResult:
    content = args.get("content")
    if not isinstance(content, str):
        return ToolResult.fail("content muss ein String sein")
    try:
        service.save_agent(ctx.user_id, content)
    except ScratchpadTooLarge as e:
        return ToolResult.fail(str(e))
    return ToolResult.ok("Agent-Notizen gespeichert.")


READ_TOOL = Tool(name="read_scratchpad", description=_READ_DESCRIPTION, schema=_READ_SCHEMA,
                 execute=_read, category="scratchpad", prompt_hint=_PROMPT_HINT)
WRITE_TOOL = Tool(name="write_scratchpad", description=_WRITE_DESCRIPTION, schema=_WRITE_SCHEMA,
                  execute=_write, category="scratchpad")
