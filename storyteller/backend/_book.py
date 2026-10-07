"""Storyteller — Bücher: Kopf, Liste, Papierkorb, Struktur (Spec 1b §2/§3).

    storyteller/books/<id>/book.json        Kopf (Titel, Art, Sprache, …, model, version)
    storyteller/books/<id>/structure.json   Teile → Kapitel → Szenen-IDs + Steckbriefe (Reihenfolge NUR hier)
    storyteller/books/<id>/scenes/<id>.md   Szenentext (reines Markdown, für Agenten lesbar)
    storyteller/books/<id>/scenes/<id>.json Szenen-Infos inkl. version
Jede Änderung prüft die Version, auf der der Client aufbaut → ``Conflict`` statt still zu überschreiben.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._files import StoryError, check_id, inside, new_id, read_json, story_root, write_json, write_scene
from ._ghost_settings import GHOST_DEFAULTS, ghost_of, merge_ghost
from ._locks import locked
from ._names import KINDS, LANGUAGES, default_names
from ._structure import validate_structure

MAX_SCENE_BYTES = 200_000
MAX_SCENES = 2000
_BOOK_FIELDS = {"title": 200, "audience": 200, "idea": 2000, "notes": 50_000, "model": 200}


class Conflict(Exception):
    """Version veraltet: ``current`` ist der Stand auf dem Server."""

    def __init__(self, current: dict):
        super().__init__("version_conflict")
        self.current = current


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def books_dir(project_id: str) -> Path:
    return story_root(project_id) / "books"


def book_dir(project_id: str, book_id: str) -> Path:
    return inside(books_dir(project_id), check_id(book_id, "book"))


def _existing(project_id: str, book_id: str) -> Path:
    d = book_dir(project_id, book_id)
    if not (d / "book.json").is_file():
        raise StoryError("book_not_found", 404)
    return d


def _clip(fields: dict[str, int], data: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, limit in fields.items():
        if k in data:
            v = data[k]
            if not isinstance(v, str) or len(v) > limit:
                raise StoryError(f"{k}_invalid")
            out[k] = v
    return out


# ---- Bücher -------------------------------------------------------------------------

def create_book(project_id: str, data: dict[str, Any]) -> dict:
    head = _clip(_BOOK_FIELDS, data)
    if not head.get("title", "").strip():
        raise StoryError("title_required")
    kind, language = data.get("kind"), data.get("language", "de")
    if kind not in KINDS or language not in LANGUAGES:
        raise StoryError("kind_or_language_invalid")
    names = default_names(kind, language)
    bid, cid, pid, sid = new_id(), new_id(), new_id(), new_id()
    book = {"id": bid, "kind": kind, "language": language, "audience": "", "idea": "", "notes": "", "model": "",
            **head, "title": head["title"].strip(), "ghost": dict(GHOST_DEFAULTS),
            "version": 1, "created_at": _now(), "updated_at": _now()}
    structure = {"version": 1, "entities": [], "parts": [
        {"id": pid, "title": names.part, "chapters": [{"id": cid, "title": names.chapter(1), "scenes": [sid]}]}]}
    d = book_dir(project_id, bid)
    write_scene(d, sid, {"id": sid, "title": names.scene(1), "summary": "", "pov": "", "status": "idea",
                          "origin": "human", "version": 1, "updated_at": _now()}, "")
    write_json(d / "structure.json", structure)
    write_json(d / "book.json", book)  # zuletzt: erst dann gilt das Buch als vorhanden
    return book


def get_book(project_id: str, book_id: str) -> dict:
    book = read_json(_existing(project_id, book_id) / "book.json")
    return {**book, "ghost": ghost_of(book)}


@locked
def update_book(project_id: str, book_id: str, data: dict[str, Any], base_version: int) -> dict:
    book = get_book(project_id, book_id)
    if book["version"] != base_version:
        raise Conflict(book)
    patch = _clip(_BOOK_FIELDS, data)
    if "title" in patch and not patch["title"].strip():
        raise StoryError("title_required")
    if "ghost" in data:
        patch["ghost"] = merge_ghost(book["ghost"], data["ghost"])
    book.update(patch, version=book["version"] + 1, updated_at=_now())
    write_json(book_dir(project_id, book_id) / "book.json", book)
    return book


def list_books(project_id: str) -> list[dict]:
    root = books_dir(project_id)
    out = []
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        if (d / "book.json").is_file():
            b = read_json(d / "book.json")
            b["words"] = sum(_words(p.read_text(encoding="utf-8")) for p in (d / "scenes").glob("*.md"))
            out.append(b)
    return sorted(out, key=lambda b: b.get("updated_at", ""), reverse=True)


@locked
def delete_book(project_id: str, book_id: str) -> None:
    """Nicht löschen, sondern in den Papierkorb verschieben."""
    d = _existing(project_id, book_id)
    trash = story_root(project_id) / "trash"
    trash.mkdir(parents=True, exist_ok=True)
    shutil.move(str(d), str(trash / f"{book_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"))


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


# ---- Struktur -----------------------------------------------------------------------

def get_structure(project_id: str, book_id: str) -> dict:
    return read_json(_existing(project_id, book_id) / "structure.json")


@locked
def save_structure(project_id: str, book_id: str, structure: dict, base_version: int) -> dict:
    d = _existing(project_id, book_id)
    current = read_json(d / "structure.json")
    if current["version"] != base_version:
        raise Conflict(current)
    existing = {p.stem for p in (d / "scenes").glob("*.json")}
    clean = validate_structure(structure, existing)
    clean["version"] = current["version"] + 1
    write_json(d / "structure.json", clean)
    return clean


