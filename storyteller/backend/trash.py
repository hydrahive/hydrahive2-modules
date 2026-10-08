"""A3 – Papierkorb ansehen und wiederherstellen (Spec nichts-geht-verloren.md §3).

Szenen: ``storyteller/trash/<buch>/scenes/<szene>-<zeit>/`` (Aufbau siehe _trash.py). Wiederherstellen legt Text,
Infos, Schnappschüsse, offene Vorschläge und deren Verlauf zurück ins Buch – an die alte Stelle (Kapitel + nach der
Vorgängerszene, sonst Kapitelanfang), wenn es das Kapitel noch gibt, sonst ans Ende des ersten Kapitels. Die
Szenen-ID bleibt; ist sie schon wieder im Buch, gibt es einen Fehler statt Überschreiben.
Bücher: siehe trash_books.py. Alles Ändernde unter der Sperre des Buchs.
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ._book import MAX_SCENES, _existing, _now
from ._files import StoryError, inside, read_json, story_root, write_json
from ._locks import locked
from ._replaced import scene_dirs

_ENTRY_RE = re.compile(r"^([a-f0-9]{32})-(\d{8}T\d{12})$")


def _scenes_dir(project_id: str, book_id: str) -> Path:
    _existing(project_id, book_id)
    return story_root(project_id) / "trash" / book_id / "scenes"


def _entry(project_id: str, book_id: str, entry_id: str) -> tuple[Path, str, str]:
    m = _ENTRY_RE.match(entry_id) if isinstance(entry_id, str) else None
    if not m:
        raise StoryError("trash_entry_not_found", 404)
    d = inside(_scenes_dir(project_id, book_id), entry_id)
    if not d.is_dir():
        raise StoryError("trash_entry_not_found", 404)
    return d, m.group(1), m.group(2)


def _deleted_at(stamp: str) -> str:
    return datetime.strptime(stamp, "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


def _info(d: Path, scene_id: str, stamp: str, chapters: set[str]) -> dict:
    place = read_json(d / "place.json") if (d / "place.json").is_file() else {}
    meta = read_json(d / f"{scene_id}.json") if (d / f"{scene_id}.json").is_file() else {}
    text = (d / f"{scene_id}.md").read_text(encoding="utf-8") if (d / f"{scene_id}.md").is_file() else ""
    words = place.get("words", sum(1 for w in text.split() if any(c.isalnum() for c in w)))
    return {"id": d.name, "scene_id": scene_id, "title": place.get("title") or meta.get("title", ""),
            "summary": meta.get("summary", ""), "words": words, "deleted_at": place.get("deleted_at") or _deleted_at(stamp),
            "chapter_id": place.get("chapter_id", ""), "chapter_title": place.get("chapter_title", ""),
            "after": place.get("after", ""), "chapter_exists": place.get("chapter_id", "") in chapters}


def list_scenes(project_id: str, book_id: str) -> list[dict]:
    root = _scenes_dir(project_id, book_id)
    st = read_json(_existing(project_id, book_id) / "structure.json")
    chapters = {c["id"] for p in st["parts"] for c in p["chapters"]}
    found = []
    for d in root.iterdir() if root.is_dir() else []:
        m = _ENTRY_RE.match(d.name)
        if m and d.is_dir():
            found.append((m.group(2), d, m.group(1)))
    # Neueste Löschung zuerst – nach dem Zeitstempel, nicht nach dem Ordnernamen (der beginnt mit der Szenen-ID).
    return [_info(d, sid, stamp, chapters) for stamp, d, sid in sorted(found, key=lambda x: x[0], reverse=True)]


def _move_back(src: Path, book: Path, scene_id: str) -> None:
    """Dateien zurück an ihre Plätze im Buch (Gegenstück zu _trash.trash_scene)."""
    moves = [(src / f"{scene_id}.md", inside(book, "scenes", f"{scene_id}.md")),
             (src / f"{scene_id}.json", inside(book, "scenes", f"{scene_id}.json")),
             (src / "snapshots", inside(book, "snapshots", scene_id)),
             (src / "proposal.md", inside(book, "proposals", f"{scene_id}.md")),
             (src / "proposal.json", inside(book, "proposals", f"{scene_id}.json")),
             (src / "proposal.info.json", inside(book, "proposals", f"{scene_id}.meta.json")),
             *((src / "history" / kind, d) for kind, d in scene_dirs(book, scene_id).items())]
    for a, b in moves:
        if a.exists():
            b.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(a), str(b))
    shutil.rmtree(src)


@locked
def restore_scene(project_id: str, book_id: str, entry_id: str) -> dict:
    src, scene_id, _stamp = _entry(project_id, book_id, entry_id)
    book = _existing(project_id, book_id)
    st = read_json(book / "structure.json")
    chapters = [c for p in st["parts"] for c in p["chapters"]]
    if any(scene_id in c["scenes"] for c in chapters) or inside(book, "scenes", f"{scene_id}.json").exists():
        raise StoryError("scene_exists", 409)
    if sum(len(c["scenes"]) for c in chapters) >= MAX_SCENES:
        raise StoryError("too_many_scenes")
    if not (src / f"{scene_id}.json").is_file():
        raise StoryError("trash_entry_broken", 409)
    place = read_json(src / "place.json") if (src / "place.json").is_file() else {}
    target = next((c for c in chapters if c["id"] == place.get("chapter_id")), None)
    if target is not None:
        after = place.get("after", "")
        at = target["scenes"].index(after) + 1 if after in target["scenes"] else 0
        placed = "original"
    else:
        target, at, placed = chapters[0], len(chapters[0]["scenes"]), "end"
    _move_back(src, book, scene_id)
    target["scenes"].insert(at, scene_id)
    st["version"] += 1
    write_json(book / "structure.json", st)
    book_meta = read_json(book / "book.json")
    write_json(book / "book.json", {**book_meta, "updated_at": _now()})
    from .scenes import get_scene
    return {"placed": placed, "chapter_id": target["id"], "scene": get_scene(project_id, book_id, scene_id),
            "structure": st}
