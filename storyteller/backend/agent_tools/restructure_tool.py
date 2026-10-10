"""Storyteller-Agent-Werkzeug C2: Gliederung umbauen (Spec autor-gliederung-c2.md §2).

Standard: Umbau-Vorschlag, den der Mensch im Storyteller übernimmt. Direkt nur, wenn (a) im Buch der Schalter
„Autor darf die Gliederung direkt ändern“ an ist (``ghost.agent_structure == "direct"``) UND (b) der aufrufende Agent
der Autor ist (Projekt-Agent des Projekts). Helfer legen immer Vorschläge ab (Grundsatz T1).
"""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import restructure, storage
from .._files import StoryError
from .._restructure_plan import MAX_STEPS
from . import agent_name, replaced_note, scope

_WHY = {
    "last_chapter": "das letzte Kapitel des Buchs bleibt",
    "chapter_empty": "ein Kapitel bliebe leer – löschen (delete_chapter) oder eine Szene hineinlegen",
    "chapter_not_found": "Kapitel nicht gefunden (IDs aus storyteller_outline, neue als new:1, new:2 …)",
    "scene_not_found": "Szene nicht gefunden (IDs aus storyteller_outline, neue als new:1, new:2 …)",
    "after_invalid": "after_… zeigt auf nichts Passendes (oder auf sich selbst)",
    "title_invalid": "Titel fehlt oder ist länger als 200 Zeichen",
    "summary_invalid": "Zusammenfassung zu lang",
    "scenes_invalid": "add_chapter braucht scenes: [{title, summary?}, …] mit mindestens einer Szene",
    "too_many_scenes": "zu viele Szenen im Buch",
    "op_invalid": "unbekannte op",
    "steps_invalid": f"steps muss eine Liste mit 1–{MAX_STEPS} Schritten sein",
    "run_active": "gerade läuft ein Ghostwriter-Lauf an diesem Buch – später noch einmal",
    "job_active": "gerade läuft ein Team-Auftrag an diesem Buch – später noch einmal",
}


def _is_author(pid: str, ctx: ToolContext) -> bool:
    from hydrahive.projects import config as project_config
    project = project_config.get(pid) or {}
    return bool(ctx.agent_id) and project.get("agent_id") == ctx.agent_id


def _fail(exc: StoryError) -> ToolResult:
    step = exc.detail.get("step")
    where = f"Schritt {step} ({exc.detail.get('op')}): " if step else ""
    extra = f" „{exc.detail['title']}“" if exc.code == "chapter_empty" and exc.detail.get("title") else ""
    return ToolResult.fail(f"Nichts geändert. {where}{_WHY.get(exc.code, exc.code)}{extra}.")


async def _restructure(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx, "write")
    if err:
        return err
    book_id = str(args.get("book_id") or "")
    try:
        book = storage.get_book(pid, book_id)
    except StoryError:
        return ToolResult.fail("Buch gibt es in diesem Projekt nicht (storyteller_books).")
    steps, note = args.get("steps"), str(args.get("note") or "")[:500]
    direct = book["ghost"].get("agent_structure") == "direct" and _is_author(pid, ctx)
    try:
        if direct:
            out = restructure.execute(pid, book_id, steps)
            return ToolResult.ok({"mode": "direct", "lines": out["lines"], "ids": out["ids"],
                                  "message": "Ausgeführt. Gelöschtes liegt im Papierkorb des Buchs und lässt sich dort "
                                             "wiederherstellen."})
        p = restructure.propose(pid, book_id, steps, author=agent_name(ctx), note=note, session_id=ctx.session_id or "")
    except StoryError as exc:
        return _fail(exc)
    return ToolResult.ok({"mode": "proposal", "lines": p["lines"], "after": p["after"], **replaced_note(p),
                          "message": "Umbau-Vorschlag liegt bereit; der Mensch übernimmt oder verwirft ihn im Storyteller "
                                     "(KI → Kapitel/Buch). Das Buch ist unverändert."})


_ID = {"type": "string"}
RESTRUCTURE = Tool(
    name="storyteller_restructure",
    description=(
        "Gliederung umbauen: Kapitel umbenennen/anlegen/löschen/verschieben, Szenen anlegen/löschen/verschieben, "
        "Kapitel-Zusammenfassung setzen – mehrere Schritte in einem Aufruf, der Reihe nach. Wird erst komplett geprüft; "
        "bei einem Fehler passiert nichts. Je nach Einstellung des Buchs direkt ausgeführt oder als Umbau-Vorschlag "
        "abgelegt (die Antwort sagt mode). Gelöschtes kommt in den Papierkorb. Neue Kapitel/Szenen in späteren "
        "Schritten als new:1, new:2 … ansprechen. Szenentext schreibt dieses Werkzeug nicht (storyteller_propose_text)."),
    schema={"type": "object", "required": ["book_id", "steps"], "properties": {
        "book_id": {"type": "string", "description": "ID des Buchs."},
        "steps": {"type": "array", "maxItems": MAX_STEPS, "description": "Schritte in Reihenfolge.", "items": {
            "type": "object", "required": ["op"], "properties": {
                "op": {"type": "string", "enum": ["rename_chapter", "add_chapter", "add_scene", "delete_chapter",
                                                  "delete_scene", "move_scene", "move_chapter", "set_chapter_summary"]},
                "chapter_id": {**_ID, "description": "Kapitel (ID oder new:n)."},
                "scene_id": {**_ID, "description": "Szene (ID oder new:n)."},
                "title": {"type": "string", "description": "Titel (rename_chapter, add_chapter, add_scene)."},
                "summary": {"type": "string", "description": "Zusammenfassung (add_scene; set_chapter_summary)."},
                "after_chapter_id": {**_ID, "description": "add_chapter/move_chapter: danach einfügen; \"\" = an den "
                                                           "Anfang des Buchs; weglassen = ans Ende."},
                "after_scene_id": {**_ID, "description": "add_scene/move_scene: danach einfügen; \"\" = an den Anfang "
                                                         "des Kapitels; weglassen = ans Ende."},
                "scenes": {"type": "array", "description": "add_chapter: Szenen des neuen Kapitels (mind. eine).",
                           "items": {"type": "object", "required": ["title"],
                                     "properties": {"title": {"type": "string"}, "summary": {"type": "string"}}}},
            }}},
        "note": {"type": "string", "description": "Optional: kurze Begründung für den Menschen."},
    }},
    execute=_restructure, category="storyteller",
)
