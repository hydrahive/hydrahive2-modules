"""Agent-Tool blueprint_propose: einen Entwurf als Vorschlag am Board ablegen (Etappe 3a).

Der Agent liefert nur Inhalte. proposal.py prüft sie und rechnet die Anordnung aus,
proposals.py legt das Ergebnis neben die Fassung des Nutzers. Überschrieben wird die
Fassung des Nutzers nie: Nur ein leeres Board wird direkt gezeichnet.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from . import access, proposal, proposals, store
from .catalog import SUBTYPES
from .tools import find_board

_MAX_NAME = 120
_MAX_NOTE = proposals.MAX_NOTE
_DESCRIPTION = (
    "Legt einen Entwurf auf einem Blueprint-Board ab: wie etwas aussehen, ablaufen und gebaut werden könnte. "
    "Du lieferst nur Inhalte (Bausteine und Verbindungen), keine Koordinaten; die Anordnung entsteht automatisch. "
    "Genau eines angeben: 'board' (ID oder Name eines vorhandenen Boards) oder 'name' (neues Board). "
    "Ein leeres oder neues Board wird direkt gezeichnet. Hat das Board schon Inhalt, wird der Entwurf als "
    "Vorschlag daneben abgelegt; der Nutzer übernimmt oder verwirft ihn, seine Fassung bleibt unverändert. "
    f"Höchstens {proposal.MAX_NODES} Bausteine."
)
_SCHEMA = {
    "type": "object",
    "properties": {
        "board": {"type": "string", "description": "ID oder Name eines vorhandenen Boards."},
        "name": {"type": "string", "description": f"Name für ein neues Board (höchstens {_MAX_NAME} Zeichen)."},
        "nodes": {
            "type": "array",
            "description": (
                "Bausteine. Layout: Seite, Karte, Button … Ablauf: Event, Aktion, Bedingung … "
                "Aufbau: Modul, Datei …"
            ),
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string",
                            "description": "Kürzel, eindeutig im Vorschlag (Buchstaben, Ziffern, _ und -)."},
                    "type": {"type": "string", "enum": list(SUBTYPES), "description": "Art des Bausteins."},
                    "label": {"type": "string", "description": f"Beschriftung (höchstens {proposal.MAX_LABEL} Zeichen)."},
                    "note": {"type": "string", "description": "Optional: Erläuterung zum Baustein."},
                    "placeholder": {"type": "string", "description": "Optional, nur beim Eingabefeld (input)."},
                },
                "required": ["key", "type", "label"],
            },
        },
        "edges": {
            "type": "array",
            "description": (
                "Verbindungen zwischen Bausteinen. event und note haben keinen Eingang, "
                "display und note keinen Ausgang."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "from": {"type": "string", "description": "Kürzel des Bausteins, von dem die Verbindung ausgeht."},
                    "to": {"type": "string", "description": "Kürzel des Ziel-Bausteins."},
                    "branch": {"type": "string", "enum": ["ja", "nein"],
                               "description": "Nur und immer bei Verbindungen, die von einer Bedingung ausgehen."},
                },
                "required": ["from", "to"],
            },
        },
        "note": {"type": "string",
                 "description": f"Kurz, was der Entwurf zeigt oder was sich geändert hat (höchstens {_MAX_NOTE} Zeichen)."},
    },
    "required": ["nodes"],
}
_HINT = (
    "\n\nBlueprint-Entwurf: Soll etwas als Board skizziert oder ein Board überarbeitet werden, nutze "
    "`blueprint_propose`. Lies ein vorhandenes Board vorher mit `blueprint_read` und baue auf der Fassung "
    "des Nutzers auf. Du überschreibst sie nie: Hat das Board Inhalt, entsteht ein Vorschlag, den der Nutzer "
    "übernimmt oder verwirft."
)


def _target(user: str, args: dict, ctx: ToolContext) -> tuple[dict | None, str | None, str | None]:
    """Liefert (vorhandenes Board, Name für ein neues Board, Fehlertext)."""
    ref, name = str(args.get("board") or "").strip(), str(args.get("name") or "").strip()
    if bool(ref) == bool(name):
        return None, None, "Genau eines angeben: 'board' (vorhandenes Board) oder 'name' (neues Board)."
    if ref:
        board, error = find_board(user, ref)
        return board, None, error
    if len(name) > _MAX_NAME:
        return None, None, f"Der Name ist zu lang ({len(name)} Zeichen, höchstens {_MAX_NAME})."
    return None, name, None


async def _execute(args: dict, ctx: ToolContext) -> ToolResult:
    user = ctx.user_id
    if not user:
        return ToolResult.fail("Kein User-Kontext verfügbar.")
    note = args.get("note") or ""
    if not isinstance(note, str) or len(note.strip()) > proposals.MAX_NOTE:
        return ToolResult.fail(f"'note' muss ein Text mit höchstens {proposals.MAX_NOTE} Zeichen sein.")
    board, new_name, error = _target(user, args, ctx)
    if error:
        return ToolResult.fail(error)
    # Erst prüfen, dann anlegen: Ein unbrauchbarer Vorschlag hinterlässt kein leeres Board.
    try:
        graph = proposal.build_graph(args.get("nodes"), args.get("edges"))
    except proposal.ProposalError as exc:
        return ToolResult.fail(exc.message)
    created = board is None
    if board is None:
        try:
            board = store.create(user, new_name, project_id=access.session_project(user, ctx.project_id))
        except store.BoardError:
            return ToolResult.fail(
                "Der Nutzer hat die Höchstzahl an Boards erreicht. Ein vorhandenes Board mit 'board' angeben.")
    result = proposals.put(user, board["id"], graph, note)
    if result is None:
        return ToolResult.fail("Das Board gibt es nicht mehr.")

    size = f"{len(graph['nodes'])} Bausteine, {len(graph['edges'])} Verbindungen"
    label = f"Board „{board['name']}“ (ID {board['id']})"
    if created:
        text = f"{label} angelegt und direkt gezeichnet: {size}."
    elif result["drawn"]:
        text = f"{label} war leer, der Entwurf ist direkt gezeichnet: {size}."
    else:
        text = (f"Vorschlag für {label} abgelegt: {size}. Die Fassung des Nutzers ist unverändert. "
                "Der Nutzer übernimmt oder verwirft den Vorschlag im Board.")
    if result["replaced"]:
        text += " Ein älterer offener Vorschlag wurde ersetzt."
    return ToolResult.ok(f"{text}\nÖffnen: /blueprint?board={board['id']}")


PROPOSE_TOOL = Tool(name="blueprint_propose", description=_DESCRIPTION, schema=_SCHEMA,
                    execute=_execute, category="blueprint", prompt_hint=_HINT)
