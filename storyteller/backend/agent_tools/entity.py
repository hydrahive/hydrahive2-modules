"""Storyteller-Agent-Werkzeug G4c: Steckbrief neu anlegen oder ändern – als Vorschlag (Spec §11.5)."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import proposals_entities, storage
from .._files import StoryError
from . import scope

_FAIL = {
    "entity_invalid": "Ungültig: Art (character/place/item) und Name sind für neue Steckbriefe Pflicht; Name/Spitznamen "
                      "≤ 200, Beschreibung ≤ 10 000 Zeichen, fields = Liste von {key, value}.",
    "nothing_changed": "Nichts vorgeschlagen: die Felder sind unverändert (die Art eines Steckbriefs lässt sich nicht ändern).",
    "entity_not_found": "Diesen Steckbrief gibt es nicht (storyteller_outline zeigt die IDs unter entities).",
    "too_many_proposals": "Zu viele offene neue Steckbriefe – erst übernehmen oder verwerfen lassen.",
}


async def _propose_entity(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    book_id, entity_id = str(args.get("book_id") or ""), str(args.get("entity_id") or "")
    changes = {k: args[k] for k in ("kind", "name", "aliases", "description", "fields") if k in args}
    try:
        storage.get_book(pid, book_id)
        replaced = bool(entity_id) and any(p["entity_id"] == entity_id for p in proposals_entities.list_for_book(pid, book_id))
        p = proposals_entities.store(pid, book_id, entity_id or None, changes, source="agent",
                                     session_id=ctx.session_id or "", note=str(args.get("note") or "")[:500])
    except StoryError as exc:
        if exc.code == "entity_exists":
            return ToolResult.fail(f"Den Steckbrief „{exc.detail['name']}“ gibt es schon (entity_id {exc.detail['entity_id']}). "
                                   "Für Änderungen diese entity_id angeben.")
        return ToolResult.fail(_FAIL.get(exc.code, "Buch gibt es in diesem Projekt nicht (storyteller_books)."))
    return ToolResult.ok({"stored": True, "proposal_id": p["id"], "new": not p["entity_id"], "fields": list(p["changes"]),
                          "replaced": replaced,
                          "message": "Steckbrief-Vorschlag liegt bereit; der Autor übernimmt oder verwirft ihn im Storyteller. "
                                     "Die Steckbriefe selbst sind unverändert."})


PROPOSE_ENTITY = Tool(
    name="storyteller_propose_entity",
    description="Steckbrief (Figur, Ort, Gegenstand) als VORSCHLAG neu anlegen (ohne entity_id; kind + name Pflicht) oder "
                "ändern (mit entity_id; nur geänderte Felder). Ändert nichts direkt; der Autor übernimmt im Storyteller.",
    schema={"type": "object", "required": ["book_id"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "entity_id": {"type": "string", "description": "Nur zum Ändern: ID des Steckbriefs (aus storyteller_outline)."},
        "kind": {"type": "string", "enum": ["character", "place", "item"], "description": "Nur bei neuen Steckbriefen."},
        "name": {"type": "string", "description": "Name (≤ 200 Zeichen)."},
        "aliases": {"type": "array", "items": {"type": "string"}, "description": "Spitznamen/andere Namen (vollständige Liste)."},
        "description": {"type": "string", "description": "Beschreibung."},
        "fields": {"type": "array", "description": "Eigenschaften (vollständige neue Liste), z. B. Alter, Augenfarbe.",
                   "items": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}}},
        "note": {"type": "string", "description": "Optional: kurze Notiz für den Autor (z. B. aus welcher Szene)."},
    }},
    execute=_propose_entity, category="storyteller",
)
