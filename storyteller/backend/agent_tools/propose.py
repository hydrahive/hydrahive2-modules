"""Storyteller-Agent-Werkzeug: Szenentext als Vorschlag ablegen (Spec §11.1/§11.2).

Die Szene selbst wird nie geändert. Der Vorschlag liegt unter proposals/<szene> mit Herkunft „agent“ und der
Chat-Sitzung; der Autor sieht ihn im Storyteller und übernimmt (Schnappschuss, Versionsprüfung) oder verwirft.
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import proposals, proposals_info, storage
from .._files import StoryError
from . import scope

SHRINK = 0.5   # Vorschlag unter der Hälfte der Szene → Warnung (Task 29fb3911)


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


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
    scene_words = _words(scene["text"])
    try:
        info = proposals.store(pid, book_id, scene_id, text.strip(), run_id="", model="", base_version=scene["version"],
                               source="agent", session_id=ctx.session_id or "", note=str(args.get("note") or "")[:500],
                               scene_words=scene_words)
    except StoryError as exc:
        return ToolResult.fail("Text zu lang für eine Szene." if exc.code == "text_too_long" else f"Nicht abgelegt: {exc.code}")
    out = {"stored": True, "scene_id": scene_id, "words": info["words"], "replaced": replaced,
           "message": "Vorschlag liegt an der Szene bereit; der Autor übernimmt oder verwirft ihn im "
                      "Storyteller. Die Szene selbst ist unverändert."}
    if info["words"] < scene_words * SHRINK:      # leere Szene (0 Wörter) warnt nie
        out["warning"] = (f"Der Vorschlag ({info['words']} Wörter) ist deutlich kürzer als die Szene ({scene_words} "
                          "Wörter). Beim Übernehmen ersetzt er die ganze Szene. Falls du die Szene nur teilweise gelesen "
                          "hast: mit storyteller_read und offset zu Ende lesen und den vollständigen Text vorschlagen.")
    return ToolResult.ok(out)


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


async def _propose_info(args: dict, ctx: ToolContext) -> ToolResult:
    """G4b: Titel, Zusammenfassung, Perspektive einer Szene als Vorschlag (Spec §11.5)."""
    pid, err = scope(ctx, "write")
    if err:
        return err
    book_id, scene_id = str(args.get("book_id") or ""), str(args.get("scene_id") or "")
    fields = {k: args[k] for k in proposals_info.FIELDS if isinstance(args.get(k), str)}
    try:
        scene = storage.get_scene(pid, book_id, scene_id)
        replaced = any(p["scene_id"] == scene_id for p in proposals_info.list_for_book(pid, book_id))
        info = proposals_info.store(pid, book_id, scene_id, fields, base_version=scene["version"], source="agent",
                                    session_id=ctx.session_id or "", note=str(args.get("note") or "")[:500])
    except StoryError as exc:
        if exc.code == "nothing_changed":
            return ToolResult.fail("Nichts vorgeschlagen: alle Felder fehlen oder sind unverändert (title, summary, pov).")
        if exc.code.endswith("_invalid"):
            return ToolResult.fail(f"Ungültig: {exc.code} (Titel/Perspektive ≤ 200, Zusammenfassung ≤ 2000 Zeichen).")
        return ToolResult.fail("Buch oder Szene gibt es in diesem Projekt nicht (storyteller_outline zeigt die IDs).")
    return ToolResult.ok({"stored": True, "scene_id": scene_id, "fields": list(info["fields"]), "replaced": replaced,
                          "message": "Vorschlag für die Szenen-Infos liegt bereit; der Autor übernimmt ihn im Reiter "
                                     "„Szene“ ganz oder teilweise. Die Szene selbst ist unverändert."})


PROPOSE_INFO = Tool(
    name="storyteller_propose_scene_info",
    description="Titel, Zusammenfassung und/oder Perspektive einer Szene als VORSCHLAG ablegen (nur geänderte Felder). "
                "Ändert die Szene nicht; der Autor übernimmt im Storyteller. Ersetzt einen älteren Infos-Vorschlag.",
    schema={"type": "object", "required": ["book_id", "scene_id"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "scene_id": {"type": "string", "description": "ID der Szene."},
        "title": {"type": "string", "description": "Neuer Titel (≤ 200 Zeichen)."},
        "summary": {"type": "string", "description": "Neue Zusammenfassung, 2–4 Sätze (≤ 2000 Zeichen). Der Ghostwriter "
                                                     "schreibt daraus; sie ist auch das Gedächtnis des Buchs."},
        "pov": {"type": "string", "description": "Perspektive: Name der Figur (Steckbrief), aus deren Sicht erzählt wird."},
        "note": {"type": "string", "description": "Optional: kurze Notiz für den Autor."},
    }},
    execute=_propose_info, category="storyteller",
)
