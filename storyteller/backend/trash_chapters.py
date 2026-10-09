"""C1 – gelöschte Kapitel ansehen und wiederherstellen (Spec loeschen-c1.md). Aufbau des Papierkorbs: _trash_chapter.py.

Wiederherstellen legt das Kapitel mit allen Szenen (Text, Infos, Schnappschüsse, Vorschläge, Verlauf), Interview und
Kapitel-Zusammenfassung zurück: in denselben Teil nach dem Vorgänger-Kapitel (Kapitelanfang des Teils, wenn es keinen
gab). Gibt es den Vorgänger nicht mehr → ans Ende des Teils; gibt es den Teil nicht mehr → ans Ende des letzten Teils.
Sind Kapitel- oder Szenen-IDs schon wieder im Buch, gibt es 409 und nichts ändert sich.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ._book import MAX_SCENES, _existing, _now
from ._files import StoryError, inside, read_json, story_root, write_json
from ._locks import locked
from .trash import _move_back

_ENTRY_RE = re.compile(r"^([a-f0-9]{32})-(\d{8}T\d{12})$")


def _root(project_id: str, book_id: str) -> Path:
    _existing(project_id, book_id)
    return story_root(project_id) / "trash" / book_id / "chapters"


def _entry(project_id: str, book_id: str, entry_id: str) -> Path:
    if not isinstance(entry_id, str) or not _ENTRY_RE.match(entry_id):
        raise StoryError("trash_entry_not_found", 404)
    d = inside(_root(project_id, book_id), entry_id)
    if not (d / "chapter.json").is_file():
        raise StoryError("trash_entry_not_found", 404)
    return d


def list_chapters(project_id: str, book_id: str) -> list[dict]:
    root = _root(project_id, book_id)
    rows = []
    for d in root.iterdir() if root.is_dir() else []:
        m = _ENTRY_RE.match(d.name)
        if not (m and (d / "chapter.json").is_file()):
            continue
        c = read_json(d / "chapter.json")
        rows.append((m.group(2), {"id": d.name, "chapter_id": c["chapter_id"], "title": c.get("title", ""),
                                  "scenes": len(c.get("scenes", [])), "words": c.get("words", 0),
                                  "deleted_at": c.get("deleted_at", "")}))
    return [r for _, r in sorted(rows, key=lambda x: x[0], reverse=True)]


def _target(st: dict, info: dict) -> tuple[dict, int, str]:
    part = next((p for p in st["parts"] if p["id"] == info.get("part_id")), None)
    if part is None:
        return st["parts"][-1], len(st["parts"][-1]["chapters"]), "end"
    ids = [c["id"] for c in part["chapters"]]
    after = info.get("after", "")
    if not after:
        return part, 0, "original"
    if after in ids:
        return part, ids.index(after) + 1, "original"
    return part, len(ids), "end"


@locked
def restore_chapter(project_id: str, book_id: str, entry_id: str) -> dict:
    src = _entry(project_id, book_id, entry_id)
    book = _existing(project_id, book_id)
    info = read_json(src / "chapter.json")
    st = read_json(book / "structure.json")
    chapters = [c for p in st["parts"] for c in p["chapters"]]
    in_book = {s for c in chapters for s in c["scenes"]}
    if any(c["id"] == info["chapter_id"] for c in chapters) or set(info["scenes"]) & in_book \
            or any(inside(book, "scenes", f"{s}.json").exists() for s in info["scenes"]):
        raise StoryError("chapter_exists", 409)
    if len(in_book) + len(info["scenes"]) > MAX_SCENES:
        raise StoryError("too_many_scenes")
    entries = info.get("entries", [])
    if len(entries) != len(info["scenes"]) or not all((src / "scenes" / e).is_dir() for e in entries):
        raise StoryError("trash_entry_broken", 409)
    part, at, placed = _target(st, info)
    for sid, e in zip(info["scenes"], entries):
        _move_back(src / "scenes" / e, book, sid)
    if (src / "interview.json").is_file():
        dst = inside(book, "interviews", f"{info['chapter_id']}.json")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src / "interview.json"), str(dst))
    if info.get("summary"):
        path = book / "chapters.json"
        data = read_json(path) if path.is_file() else {}
        write_json(path, {**data, info["chapter_id"]: info["summary"]})
    part["chapters"].insert(at, {"id": info["chapter_id"], "title": info["title"], "scenes": list(info["scenes"])})
    st["version"] += 1
    write_json(book / "structure.json", st)
    write_json(book / "book.json", {**read_json(book / "book.json"), "updated_at": _now()})
    shutil.rmtree(src)
    from .scenes import get_scene
    return {"placed": placed, "chapter_id": info["chapter_id"], "structure": st,
            "scenes": [get_scene(project_id, book_id, s) for s in info["scenes"]]}
