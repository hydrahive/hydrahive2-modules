"""C1 – Kapitel samt Szenen in den Papierkorb (Spec loeschen-c1.md). Aufrufer hält die Sperre des Buchs.

    storyteller/trash/<buch>/chapters/<kapitel>-<zeit>/
        chapter.json        Titel, Teil, Vorgänger-Kapitel, Szenen-IDs, Szenen-Einträge, Kapitel-Zusammenfassung
        interview.json      Interview des Kapitels (falls vorhanden)
        scenes/<eintrag>/   je Szene derselbe Aufbau wie im Szenen-Papierkorb (_trash.py)
Wiederherstellen: trash_chapters.py.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from ._files import check_id, inside, read_json, story_root, write_json
from ._trash import _words, trash_scene

_SUMMARIES = "chapters.json"   # Ablage der Kapitel-Zusammenfassungen (chapter_summaries.py)


def chapter_place(structure: dict, chapter_id: str) -> dict:
    """Teil und Vorgänger-Kapitel – VOR dem Entfernen aufrufen."""
    for p in structure["parts"]:
        ids = [c["id"] for c in p["chapters"]]
        if chapter_id in ids:
            i = ids.index(chapter_id)
            return {"part_id": p["id"], "after": ids[i - 1] if i else ""}
    return {"part_id": "", "after": ""}


def trash_chapter(project_id: str, book_id: str, book_dir: Path, chapter: dict, place: dict) -> Path:
    """Kapitel-Ordner anlegen, Szenen hineinlegen, Interview und Kapitel-Zusammenfassung mitnehmen."""
    cid = check_id(chapter["id"], "chapter")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = story_root(project_id) / "trash" / book_id / "chapters" / f"{cid}-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    words, entries = 0, []
    for sid in chapter["scenes"]:
        text_path = inside(book_dir, "scenes", f"{sid}.md")
        words += _words(text_path.read_text(encoding="utf-8")) if text_path.is_file() else 0
        entries.append(trash_scene(project_id, book_id, book_dir, sid, {"chapter_id": cid, "chapter_title": chapter["title"],
                                                                         "after": ""}, into=target / "scenes").name)
    summaries_path = book_dir / _SUMMARIES
    summaries = read_json(summaries_path) if summaries_path.is_file() else {}
    summary = summaries.pop(cid, None) if isinstance(summaries, dict) else None
    if summary is not None:
        write_json(summaries_path, summaries)
    interview = inside(book_dir, "interviews", f"{cid}.json")
    if interview.is_file():
        shutil.move(str(interview), str(target / "interview.json"))
    write_json(target / "chapter.json", {
        "chapter_id": cid, "title": chapter["title"], **place, "scenes": list(chapter["scenes"]), "entries": entries,
        "summary": summary, "words": words, "deleted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return target
