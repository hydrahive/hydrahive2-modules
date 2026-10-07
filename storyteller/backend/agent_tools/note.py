"""Storyteller-Agent-Werkzeuge T1d: Hinweise/Notizen ablegen und lesen (Spec schreib-team.md §5).

Ändert nie das Buch – Einträge liegen neben dem Buch (``notes/``), der Mensch hakt ab oder verwirft sie.
Herkunft (Agent, Sitzung) kommt aus dem ToolContext, nicht aus den Argumenten.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import storage, team_notes
from .._files import StoryError
from . import scope

_FAIL = {
    "note_invalid": "Ungültig: kind = hint oder note, Titel (≤ 200) und Text (≤ 4000 Zeichen) Pflicht, "
                    "höchstens 10 Quellen mit http(s)-Adresse.",
    "place_not_found": "Diese Stelle gibt es nicht (scene_id/chapter_id/entity_id aus storyteller_outline).",
    "too_many_notes": "Zu viele offene Hinweise im Buch – erst abhaken lassen.",
}


def _author(agent_id: str) -> str:
    from hydrahive.agents import config as agent_config
    agent = agent_config.get(agent_id) if agent_id else None
    return (agent or {}).get("name") or "Agent"


async def _note(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    book_id = str(args.get("book_id") or "")
    data = {k: args.get(k) for k in ("kind", "title", "text", "scene_id", "chapter_id", "entity_id", "sources")}
    data.update(author=_author(ctx.agent_id or ""), agent_id=ctx.agent_id or "", session_id=ctx.session_id or "")
    try:
        storage.get_book(pid, book_id)
        note = team_notes.add(pid, book_id, data)
    except StoryError as exc:
        return ToolResult.fail(_FAIL.get(exc.code, "Buch gibt es in diesem Projekt nicht (storyteller_books)."))
    return ToolResult.ok({"stored": True, "note_id": note["id"],
                          "open_total": len(team_notes.list_notes(pid, book_id)),
                          "message": "Liegt im Reiter „Team“ des Storytellers; der Autor hakt ab oder verwirft. "
                                     "Das Buch selbst ist unverändert."})


async def _notes(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx)
    if err:
        return err
    book_id, status = str(args.get("book_id") or ""), str(args.get("status") or "open")
    try:
        notes = team_notes.list_notes(pid, book_id, status="all" if status == "all" else "open",
                                      scene_id=str(args.get("scene_id") or "") or None)
    except StoryError:
        return ToolResult.fail("Buch gibt es in diesem Projekt nicht (storyteller_books).")
    keep = ("id", "kind", "title", "text", "sources", "author", "status", "scene_id", "chapter_id", "entity_id", "at")
    return ToolResult.ok({"notes": [{k: n[k] for k in keep if k in n} for n in notes]})


NOTE = Tool(
    name="storyteller_note",
    description="Hinweis (Befund an einer Stelle) oder Notiz (Wissen, z. B. Recherche mit Quellen) am Buch ablegen. "
                "Ändert das Buch nicht; der Autor sieht es im Reiter „Team“. Je Befund ein Eintrag, Stelle angeben.",
    schema={"type": "object", "required": ["book_id", "kind", "title", "text"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "kind": {"type": "string", "enum": ["hint", "note"], "description": "hint = Befund/Problem, note = Wissen/Idee."},
        "title": {"type": "string", "description": "Kurz, worum es geht (≤ 200 Zeichen)."},
        "text": {"type": "string", "description": "Befund mit Begründung bzw. Inhalt (≤ 4000 Zeichen)."},
        "scene_id": {"type": "string", "description": "Optional: betroffene Szene."},
        "chapter_id": {"type": "string", "description": "Optional: betroffenes Kapitel."},
        "entity_id": {"type": "string", "description": "Optional: betroffener Steckbrief."},
        "sources": {"type": "array", "description": "Optional: Quellen (≤ 10).", "items": {
            "type": "object", "properties": {"title": {"type": "string"}, "url": {"type": "string"}}}},
    }},
    execute=_note, category="storyteller",
)

NOTES = Tool(
    name="storyteller_notes",
    description="Hinweise und Notizen des Teams zum Buch lesen (Volltext, Quellen). Standard: nur offene.",
    schema={"type": "object", "required": ["book_id"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "scene_id": {"type": "string", "description": "Optional: nur zu dieser Szene."},
        "status": {"type": "string", "enum": ["open", "all"], "description": "open (Standard) oder all."},
    }},
    execute=_notes, category="storyteller",
)
