"""Storyteller-Agent-Werkzeug: Szenentext als Vorschlag ablegen (Spec §11.1/§11.2).

Die Szene selbst wird nie geändert. Der Vorschlag liegt unter proposals/<szene> mit Herkunft „agent“ und der
Chat-Sitzung; der Autor sieht ihn im Storyteller und übernimmt (Schnappschuss, Versionsprüfung) oder verwirft.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import proposals, storage
from .._files import StoryError
from . import scope


async def _propose_text(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    book_id, scene_id, text = str(args.get("book_id") or ""), str(args.get("scene_id") or ""), args.get("text")
    if not isinstance(text, str) or not text.strip():
        return ToolResult.fail("Leerer Text – nichts vorgeschlagen.")
    try:
        storage.get_book(pid, book_id)
        scene = storage.get_scene(pid, book_id, scene_id)
    except StoryError:
        return ToolResult.fail("Buch oder Szene gibt es in diesem Projekt nicht (storyteller_outline zeigt die IDs).")
    replaced = any(p["scene_id"] == scene_id for p in proposals.list_for_book(pid, book_id))
    try:
        info = proposals.store(pid, book_id, scene_id, text.strip(), run_id="", model="", base_version=scene["version"],
                               source="agent", session_id=ctx.session_id or "", note=str(args.get("note") or "")[:500])
    except StoryError as exc:
        return ToolResult.fail("Text zu lang für eine Szene." if exc.code == "text_too_long" else f"Nicht abgelegt: {exc.code}")
    return ToolResult.ok({"stored": True, "scene_id": scene_id, "words": info["words"], "replaced": replaced,
                          "message": "Vorschlag liegt an der Szene bereit; der Autor übernimmt oder verwirft ihn im "
                                     "Storyteller. Die Szene selbst ist unverändert."})


PROPOSE_TEXT = Tool(
    name="storyteller_propose_text",
    description="Neuen oder überarbeiteten Text für eine Szene als VORSCHLAG ablegen. Ändert die Szene nicht; der Autor "
                "übernimmt oder verwirft im Storyteller. Ersetzt einen älteren offenen Vorschlag derselben Szene.",
    schema={"type": "object", "required": ["book_id", "scene_id", "text"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "scene_id": {"type": "string", "description": "ID der Szene (aus storyteller_outline)."},
        "text": {"type": "string", "description": "Der vollständige neue Szenentext (Markdown, ohne Überschrift)."},
        "note": {"type": "string", "description": "Optional: kurze Notiz für den Autor (was geändert wurde)."},
    }},
    execute=_propose_text, category="storyteller",
)
