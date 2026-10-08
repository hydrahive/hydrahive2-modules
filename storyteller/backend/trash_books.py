"""A3 – gelöschte Bücher im Papierkorb des Projekts (Spec nichts-geht-verloren.md §3).

    storyteller/trash/<buch>-<zeit>/          gelöschtes Buch (delete_book) → wiederherstellbar
    storyteller/trash/moved/<buch>-<zeit>/    Sicherung nach dem Umzug in ein eigenes Projekt (T1f) → nur anzeigen
    storyteller/trash/<buch>/scenes/…         gelöschte Szenen eines lebenden Buchs (trash.py) → hier nicht

Wiederherstellen verschiebt den Ordner zurück nach ``books/<buch>``; gibt es das Buch schon, Fehler statt Überschreiben.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ._book import books_dir, get_book
from ._files import StoryError, inside, read_json, story_root
from ._locks import book_lock

_DELETED_RE = re.compile(r"^([a-f0-9]{32})-(\d{8}T\d{12})$")
_MOVED_RE = re.compile(r"^([a-f0-9]{32})-(\d{8}T\d{6})$")


def _at(stamp: str) -> str:
    fmt = "%Y%m%dT%H%M%S%f" if len(stamp) > 15 else "%Y%m%dT%H%M%S"
    return datetime.strptime(stamp, fmt).replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


def _row(d: Path, book_id: str, stamp: str, kind: str) -> dict | None:
    if not (d / "book.json").is_file():
        return None
    book = read_json(d / "book.json")
    texts = list((d / "scenes").glob("*.md")) if (d / "scenes").is_dir() else []
    words = sum(sum(1 for w in p.read_text(encoding="utf-8").split() if any(c.isalnum() for c in w)) for p in texts)
    return {"id": d.name, "kind": kind, "book_id": book_id, "title": book.get("title", ""), "scenes": len(texts),
            "words": words, "deleted_at": _at(stamp), "restorable": kind == "deleted"}


def list_books(project_id: str) -> list[dict]:
    root = story_root(project_id) / "trash"
    out = []
    for d in root.iterdir() if root.is_dir() else []:
        m = _DELETED_RE.match(d.name)
        row = _row(d, m.group(1), m.group(2), "deleted") if m and d.is_dir() else None
        out += [row] if row else []
    moved = root / "moved"
    for d in moved.iterdir() if moved.is_dir() else []:
        m = _MOVED_RE.match(d.name)
        row = _row(d, m.group(1), m.group(2), "moved") if m and d.is_dir() else None
        out += [row] if row else []
    return sorted(out, key=lambda r: r["deleted_at"], reverse=True)


def restore_book(project_id: str, entry_id: str) -> dict:
    m = _DELETED_RE.match(entry_id) if isinstance(entry_id, str) else None
    if not m:
        raise StoryError("trash_entry_not_found", 404)
    book_id = m.group(1)
    with book_lock(project_id, book_id):
        src = inside(story_root(project_id) / "trash", entry_id)
        if not (src / "book.json").is_file():
            raise StoryError("trash_entry_not_found", 404)
        dst = books_dir(project_id) / book_id
        if dst.exists():
            raise StoryError("book_exists", 409)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return get_book(project_id, book_id)
