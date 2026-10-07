"""Storyteller-Agent-Werkzeuge: lesen (Bücher, Gliederung, Szenen, Interview). Spec §11.1."""
from __future__ import annotations

from hydrahive.tools.base import Tool, ToolContext, ToolResult

from .. import (
    interviews,
    proposals,
    proposals_entities,
    proposals_info,
    proposals_outline,
    storage,
    team_notes,
)
from .._files import StoryError
from . import HINT, scope
from ._chunk import chunk

MAX_SCENES = 3
MAX_TEXT = 12_000
_CONTINUE = ("Mindestens eine Szene ist länger als ein Abschnitt (cut: true). Weiterlesen mit storyteller_read("
             "book_id, scene_ids=[<id>], offset=<next_offset>), bis next_offset null ist. Vor storyteller_propose_text "
             "die ganze Szene lesen – der Vorschlag ersetzt beim Übernehmen die komplette Szene.")


def _offset(args: dict, ids: list) -> tuple[int, str | None]:
    raw = args.get("offset")
    if raw is None:
        return 0, None
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        return 0, "offset muss eine Zahl ≥ 0 sein (next_offset aus dem letzten Aufruf)."
    if len(ids) != 1:
        return 0, "Mit offset genau eine Szene angeben (scene_ids mit einer ID)."
    return raw, None


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


def _book_or_fail(pid: str, book_id: str) -> tuple[dict | None, ToolResult | None]:
    try:
        return storage.get_book(pid, str(book_id or "")), None
    except StoryError:
        return None, ToolResult.fail(f"Buch '{book_id}' gibt es in diesem Projekt nicht (storyteller_books listet die Bücher).")


async def _books(_args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx)
    if err:
        return err
    return ToolResult.ok({"books": [{"id": b["id"], "title": b["title"], "kind": b["kind"], "language": b["language"],
                                     "words": b.get("words", 0), "idea": b.get("idea", "")} for b in storage.list_books(pid)]})


def _outline_info(p: dict | None) -> dict | None:
    if not p:
        return None
    ch = p["outline"]["chapters"]
    return {"chapters": len(ch), "scenes": sum(len(c["scenes"]) for c in ch), "titles": [c["title"] for c in ch]}


async def _outline(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx)
    if err:
        return err
    book, err = _book_or_fail(pid, args.get("book_id"))
    if err:
        return err
    st = storage.get_structure(pid, book["id"])
    open_props = {p["scene_id"] for p in proposals.list_for_book(pid, book["id"])}
    open_infos = {p["scene_id"] for p in proposals_info.list_for_book(pid, book["id"])}
    ents = {e["id"]: e["name"] for e in st.get("entities", [])}
    open_notes = team_notes.list_notes(pid, book["id"])
    note_count = team_notes.open_counts(pid, book["id"])

    def scene(sid: str) -> dict:
        s = storage.get_scene(pid, book["id"], sid)
        return {"id": sid, "title": s["title"], "summary": s["summary"], "pov": s["pov"], "status": s["status"],
                "origin": s["origin"], "words": _words(s["text"]), "has_proposal": sid in open_props,
                "has_info_proposal": sid in open_infos, "open_notes": note_count.get(sid, 0)}

    return ToolResult.ok({
        "book": {"id": book["id"], "title": book["title"], "kind": book["kind"], "language": book["language"],
                 "audience": book.get("audience", ""), "idea": book.get("idea", ""), "style": book["ghost"].get("style", "")},
        "parts": [{"id": p["id"], "title": p["title"], "chapters": [
            {"id": c["id"], "title": c["title"], "scenes": [scene(s) for s in c["scenes"]]} for c in p["chapters"]]}
            for p in st["parts"]],
        "entities": [{"id": e["id"], "kind": e["kind"], "name": e["name"], "aliases": e.get("aliases", []),
                      "description": e.get("description", ""), "fields": e.get("fields", [])} for e in st.get("entities", [])],
        "entity_proposals": [{"id": p["id"], "entity_id": p["entity_id"], "kind": p["kind"],
                              "name": p["changes"].get("name") or ents.get(p["entity_id"], ""), "fields": list(p["changes"])}
                             for p in proposals_entities.list_for_book(pid, book["id"])],
        "outline_proposal": _outline_info(proposals_outline.find(pid, book["id"])),
        "open_notes": [{k: n[k] for k in ("id", "kind", "title", "author", "scene_id", "chapter_id", "entity_id") if k in n}
                       for n in open_notes],
    })


async def _read(args: dict, ctx: ToolContext) -> ToolResult:
    pid, err = scope(ctx)
    if err:
        return err
    book, err = _book_or_fail(pid, args.get("book_id"))
    if err:
        return err
    ids = args.get("scene_ids") or []
    chapter = args.get("interview_chapter_id")
    if not isinstance(ids, list) or (not ids and not chapter):
        return ToolResult.fail("scene_ids (1–3 Szenen-IDs aus storyteller_outline) oder interview_chapter_id angeben.")
    if len(ids) > MAX_SCENES:
        return ToolResult.fail(f"Höchstens {MAX_SCENES} Szenen je Aufruf.")
    offset, bad = _offset(args, ids)
    if bad:
        return ToolResult.fail(bad)
    out: dict = {"book_id": book["id"], "scenes": []}
    for sid in ids:
        try:
            s = storage.get_scene(pid, book["id"], str(sid))
        except StoryError:
            return ToolResult.fail(f"Szene '{sid}' gibt es in diesem Buch nicht.")
        if offset and offset >= len(s["text"]):
            return ToolResult.fail(f"offset {offset} liegt hinter dem Ende der Szene ({len(s['text'])} Zeichen).")
        part, nxt = chunk(s["text"], offset, MAX_TEXT)
        out["scenes"].append({"id": s["id"], "title": s["title"], "summary": s["summary"], "version": s["version"],
                              "words": _words(s["text"]), "text": part, "offset": offset, "next_offset": nxt,
                              "total_chars": len(s["text"]), "cut": nxt is not None})
    if any(s["cut"] for s in out["scenes"]):
        out["hint"] = _CONTINUE
    if chapter:
        try:
            iv = interviews.get(pid, book["id"], str(chapter))
        except StoryError:
            return ToolResult.fail(f"Kapitel '{chapter}' gibt es in diesem Buch nicht.")
        out["interview"] = {"chapter_id": chapter, "questions": [{"question": q["question"], "answer": q["answer"]}
                                                                  for q in iv["questions"]]}
    return ToolResult.ok(out)


_BOOK = {"book_id": {"type": "string", "description": "ID des Buchs (aus storyteller_books)."}}

BOOKS = Tool(name="storyteller_books", description="Bücher im Storyteller dieses Projekts auflisten (ID, Titel, Art, Wörter).",
             schema={"type": "object", "properties": {}}, execute=_books, category="storyteller", prompt_hint=HINT)
OUTLINE = Tool(name="storyteller_outline",
               description="Gliederung eines Buchs: Teile, Kapitel, Szenen (Zusammenfassung, Perspektive, Wörter, Herkunft, "
                           "offener Vorschlag) und Steckbriefe.",
               schema={"type": "object", "required": ["book_id"], "properties": _BOOK}, execute=_outline, category="storyteller")
READ = Tool(name="storyteller_read",
            description=f"Text von 1–{MAX_SCENES} Szenen lesen (mit Version) und/oder das Interview eines Kapitels. "
                        "Lange Szenen kommen in Abschnitten (cut, next_offset) – mit offset weiterlesen.",
            schema={"type": "object", "required": ["book_id"], "properties": {
                **_BOOK,
                "scene_ids": {"type": "array", "items": {"type": "string"}, "description": f"Bis zu {MAX_SCENES} Szenen-IDs."},
                "offset": {"type": "integer", "description": "Optional, nur mit genau einer Szene: ab diesem Zeichen "
                                                             "weiterlesen (Wert von next_offset aus dem letzten Aufruf)."},
                "interview_chapter_id": {"type": "string", "description": "Optional: Kapitel-ID, dessen Interview gelesen wird."},
            }}, execute=_read, category="storyteller")
