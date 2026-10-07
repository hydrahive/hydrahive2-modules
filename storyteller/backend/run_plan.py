"""Ghostwriter G2 – welche Szenen ein Lauf schreibt und was er ungefähr kostet (Spec §9.2/§9.4)."""
from __future__ import annotations

from . import _cost, ghost, storage
from ._files import StoryError
from ._ghost_settings import ghost_of
from .runs import MAX_RUN_SCENES

SCOPES = ("chapter", "from", "book")


def scenes_in_scope(project_id: str, book_id: str, scope: str, chapter_id: str | None, scene_id: str | None) -> list[str]:
    st = storage.get_structure(project_id, book_id)
    if scope == "book":
        return [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
    if scope == "chapter":
        ch = next((c for p in st["parts"] for c in p["chapters"] if c["id"] == chapter_id), None)
        if ch is None:
            raise StoryError("chapter_not_found", 404 if chapter_id else 400)
        return list(ch["scenes"])
    if scope == "from":
        order = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
        if scene_id not in order:
            raise StoryError("scene_not_found", 404 if scene_id else 400)
        return order[order.index(scene_id):]
    raise StoryError("scope_invalid")


def plan(project_id: str, book_id: str, *, scope: str, chapter_id: str | None = None, scene_id: str | None = None,
         skip_filled: bool = True, length_words: int | None = None) -> dict:
    """Szenen zum Schreiben + Schätzung. Übersprungen: ohne Zusammenfassung, mit Text (wenn gewünscht)."""
    book = storage.get_book(project_id, book_id)
    todo, filled, no_summary = [], 0, 0
    tin = tout = 0
    for sid in scenes_in_scope(project_id, book_id, scope, chapter_id, scene_id):
        s = storage.get_scene(project_id, book_id, sid)
        if not s["summary"].strip():
            no_summary += 1
            continue
        if s["text"].strip() and skip_filled:
            filled += 1
            continue
        length, chunk = ghost.plan_lengths(book, length_words)
        e = _cost.scene_estimate(ghost.build_material(project_id, book_id, sid), length_words=length, chunk_words=chunk)
        tin, tout = tin + e["input_tokens"], tout + e["output_tokens"]
        todo.append(sid)
    if len(todo) > MAX_RUN_SCENES:
        raise StoryError("too_many_scenes")
    model = ghost.choose_model(book, None) or ""
    return {"scene_ids": todo, "scenes": len(todo), "skipped_filled": filled, "skipped_no_summary": no_summary,
            "input_tokens": tin, "output_tokens": tout, "model": model,
            "cost_micros": _cost.cost_micros(model, tokens_in=tin, tokens_out=tout),
            "limit_tokens": ghost_of(book)["limit_tokens"]}
