"""Ein ganzes Buch auf einmal anlegen (Beispielbuch, Übernahme aus dem Entwurf 0.1.0).

Erst wird alles geprüft, dann in einen Temp-Ordner geschrieben und zuletzt in einem Schritt
umbenannt: Bei einem Fehler bleibt nichts Halbes liegen.
"""
from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any

from . import storage
from ._book import _now
from ._files import StoryError, new_id, write_atomic, write_json
from ._ghost_settings import GHOST_DEFAULTS, ORIGINS
from ._names import KINDS, LANGUAGES
from ._structure import validate_structure

_STATUSES = ("idea", "draft", "revised", "done")


def _text(v: Any, limit: int, code: str) -> str:
    if v is None:
        return ""
    if not isinstance(v, str) or len(v) > limit:
        raise StoryError(code)
    return v


def _prepare(data: dict[str, Any]) -> tuple[dict, dict, list[tuple[dict, str]]]:
    title = _text(data.get("title"), 200, "title_invalid").strip()
    if not title:
        raise StoryError("title_required")
    if data.get("kind") not in KINDS or data.get("language", "de") not in LANGUAGES:
        raise StoryError("kind_or_language_invalid")
    now = _now()
    book = {"id": new_id(), "title": title, "kind": data["kind"], "language": data.get("language", "de"),
            "audience": _text(data.get("audience"), 200, "audience_invalid"),
            "idea": _text(data.get("idea"), 2000, "idea_invalid"),
            "notes": _text(data.get("notes"), 50_000, "notes_invalid"),
            "model": _text(data.get("model"), 200, "model_invalid"),
            "ghost": dict(GHOST_DEFAULTS), "version": 1, "created_at": now, "updated_at": now}
    parts_in = data.get("parts")
    if not isinstance(parts_in, list) or not parts_in:
        raise StoryError("structure_invalid")
    scenes: list[tuple[dict, str]] = []
    parts = []
    for p in parts_in:
        chapters = []
        for c in (p.get("chapters") if isinstance(p, dict) else None) or []:
            ids = []
            for s in (c.get("scenes") if isinstance(c, dict) else None) or []:
                if not isinstance(s, dict):
                    raise StoryError("structure_invalid")
                text = _text(s.get("text"), storage.MAX_SCENE_BYTES * 4, "text_too_long")
                if len(text.encode("utf-8")) > storage.MAX_SCENE_BYTES:
                    raise StoryError("text_too_long")
                status = s.get("status") if s.get("status") in _STATUSES else "draft"
                origin = s.get("origin") if s.get("origin") in ORIGINS else "human"
                meta = {"id": new_id(), "title": _text(s.get("title"), 200, "title_invalid").strip() or "…",
                        "summary": _text(s.get("summary"), 2000, "summary_invalid"),
                        "pov": _text(s.get("pov"), 200, "pov_invalid"), "status": status,
                        "origin": origin, "version": 1, "updated_at": now}
                scenes.append((meta, text))
                ids.append(meta["id"])
            chapters.append({"id": new_id(), "title": (c.get("title") if isinstance(c, dict) else None) or "…", "scenes": ids})
        parts.append({"id": new_id(), "title": (p.get("title") if isinstance(p, dict) else None) or "…", "chapters": chapters})
    if len(scenes) > storage.MAX_SCENES:
        raise StoryError("too_many_scenes")
    entities = [{**e, "id": new_id()} if isinstance(e, dict) else e for e in (data.get("entities") or [])]
    structure = validate_structure({"parts": parts, "entities": entities}, {m["id"] for m, _ in scenes})
    structure["version"] = 1
    return book, structure, scenes


def import_book(project_id: str, data: dict[str, Any]) -> dict:
    book, structure, scenes = _prepare(data)
    books = storage.books_dir(project_id)
    books.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(dir=books, prefix=".import-")
    os.chmod(tmp, stat.S_IMODE(books.stat().st_mode))  # wie der Elternordner, nicht mkdtemps 0700
    try:
        for meta, text in scenes:
            write_atomic(Path(tmp) / "scenes" / f"{meta['id']}.md", text)
            write_json(Path(tmp) / "scenes" / f"{meta['id']}.json", meta)
        write_json(Path(tmp) / "structure.json", structure)
        write_json(Path(tmp) / "book.json", book)
        os.replace(tmp, storage.book_dir(project_id, book["id"]))
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return book
