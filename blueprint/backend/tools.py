"""Agent-Tool blueprint_read: eigene Boards auflisten und als Text lesen (Task 9111b283)."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import store
from .render import render_board

_DESCRIPTION = (
    "Liest die Blueprint-Boards des Users (visuelle Skizzen von Seiten-Layouts und Abläufen). "
    "Ohne 'board': Liste der Boards. Mit 'board' (ID oder Name): das Board als Text mit "
    "Bausteinen, Beschriftungen, Notizen und Verbindungen (bei Bedingungen ja/nein). Nur lesend."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "board": {"type": "string", "description": "ID oder Name des Boards. Leer lassen für die Liste."},
    },
    "required": [],
}
_HINT = (
    "\n\nBlueprint: Verweist der User auf ein Board, eine Skizze oder einen gezeichneten Ablauf, "
    "lies es mit `blueprint_read` (erst ohne Argument für die Liste). Baue danach genau das, was "
    "das Board zeigt, statt zu raten."
)


def _list(user: str) -> ToolResult:
    boards = store.list_for(user)
    if not boards:
        return ToolResult.ok("Der User hat keine Blueprint-Boards.")
    lines = [f"{len(boards)} Blueprint-Board(s), neueste zuerst:"]
    lines += [f"- ID {b['id']}: „{b['name']}“ (geändert {b['updated_at']})" for b in boards]
    return ToolResult.ok("\n".join(lines))


def _find(user: str, ref: str) -> tuple[dict | None, str | None]:
    if ref.isdigit():
        board = store.get(user, int(ref))
        if board:
            return board, None
    boards = store.list_for(user)
    exact = [b for b in boards if b["name"] == ref]
    hits = exact or [b for b in boards if ref.lower() in b["name"].lower()]
    if len(hits) == 1:
        return store.get(user, hits[0]["id"]), None
    if not hits:
        return None, f"Kein Board „{ref}“ gefunden. Ohne Argument aufrufen für die Liste."
    names = ", ".join(f"„{b['name']}“ (ID {b['id']})" for b in hits[:10])
    return None, f"„{ref}“ ist mehrdeutig: {names}. Bitte ID oder vollständigen Namen angeben."


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    user = ctx.user_id
    if not user:
        return ToolResult.fail("Kein User-Kontext verfügbar.")
    ref = str(args.get("board") or "").strip()
    if not ref:
        return _list(user)
    board, error = _find(user, ref)
    if not board:
        return ToolResult.fail(error or "Board nicht gefunden.")
    return ToolResult.ok(render_board(board, board["graph_json"]))


READ_TOOL = Tool(name="blueprint_read", description=_DESCRIPTION, schema=_SCHEMA,
                 execute=_execute, category="blueprint", prompt_hint=_HINT)
