"""Storyteller-Agent-Werkzeug G4d: neue Kapitel/Szenen als Gliederungs-Vorschlag (Spec §11.5)."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import outline, proposals_outline, storage
from .._files import StoryError
from . import agent_name, replaced_note, scope


async def _propose_outline(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    book_id = str(args.get("book_id") or "")
    data = {"chapters": args.get("chapters"), "entities": args.get("entities") or []}
    try:
        storage.get_book(pid, book_id)
        p = proposals_outline.store(pid, book_id, data, source="agent", session_id=ctx.session_id or "",
                                    note=str(args.get("note") or "")[:500], author=agent_name(ctx))
    except StoryError as exc:
        if exc.code == "outline_invalid":
            return ToolResult.fail(f"Ungültige Gliederung: 1–{outline.MAX_CHAPTERS} Kapitel mit Titel, je 1–"
                                   f"{outline.MAX_SCENES_PER_CHAPTER} Szenen mit Titel und Zusammenfassung (≤ 2000 Zeichen).")
        return ToolResult.fail("Buch gibt es in diesem Projekt nicht (storyteller_books).")
    chapters = p["outline"]["chapters"]
    return ToolResult.ok({"stored": True, "chapters": len(chapters), "scenes": sum(len(c["scenes"]) for c in chapters),
                          **replaced_note(p),
                          "message": "Gliederungs-Vorschlag liegt bereit; der Autor sieht ihn im Storyteller (KI → "
                                     "„Kapitel/Buch“), kann ihn bearbeiten und übernehmen – dann werden die Kapitel am "
                                     "Ende angehängt. Das Buch selbst ist unverändert."})


PROPOSE_OUTLINE = Tool(
    name="storyteller_propose_outline",
    description="Neue Kapitel mit Szenen (Titel + Zusammenfassung) als GLIEDERUNGS-VORSCHLAG ablegen; beim Übernehmen "
                "werden sie am Ende des Buchs angehängt. Ändert nichts direkt. Ersetzt einen älteren Gliederungs-Vorschlag.",
    schema={"type": "object", "required": ["book_id", "chapters"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "chapters": {"type": "array", "description": "Neue Kapitel in Reihenfolge.", "items": {
            "type": "object", "required": ["title", "scenes"], "properties": {
                "title": {"type": "string"},
                "scenes": {"type": "array", "items": {"type": "object", "required": ["title", "summary"], "properties": {
                    "title": {"type": "string"}, "summary": {"type": "string", "description": "2–4 Sätze, was passiert."},
                    "pov": {"type": "string", "description": "Optional: Perspektive (Name einer Figur)."}}}}}}},
        "entities": {"type": "array", "description": "Optional: neue Figuren/Orte/Gegenstände (nur neue Namen werden angelegt).",
                     "items": {"type": "object", "properties": {"name": {"type": "string"},
                                                                "kind": {"type": "string", "enum": ["character", "place", "item"]},
                                                                "description": {"type": "string"}}}},
        "note": {"type": "string", "description": "Optional: kurze Notiz für den Autor."},
    }},
    execute=_propose_outline, category="storyteller",
)
