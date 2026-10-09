"""Gelöschte Szenen in den Papierkorb statt endgültig löschen (Fix 0.6.1) – wie ganze Bücher.

    storyteller/trash/<buch>/scenes/<szene>-<zeit>/
        <szene>.md, <szene>.json      Text und Infos
        snapshots/*.md                Schnappschüsse
        proposal.md, proposal.json    offener KI-Vorschlag (falls vorhanden)
        proposal.info.json            offener Vorschlag für Szenen-Infos (G4b)
        history/text, history/info    Verlauf ersetzter/verworfener Vorschläge (A2)
        place.json                    alte Stelle (Kapitel, Vorgängerszene) + Titel, Wörter, gelöscht am (A3)
Wiederherstellen: trash.py. Aufrufer hält die Sperre des Buchs.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._files import check_id, inside, read_json, story_root, write_json
from ._replaced import scene_dirs


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


def place_of(structure: dict, scene_id: str) -> dict[str, Any]:
    """Kapitel und Vorgängerszene – VOR dem Entfernen aus der Gliederung aufrufen."""
    for c in (c for p in structure["parts"] for c in p["chapters"]):
        if scene_id in c["scenes"]:
            i = c["scenes"].index(scene_id)
            return {"chapter_id": c["id"], "chapter_title": c["title"], "after": c["scenes"][i - 1] if i else ""}
    return {"chapter_id": "", "chapter_title": "", "after": ""}


def trash_scene(project_id: str, book_id: str, book_dir: Path, scene_id: str, place: dict | None = None,
                into: Path | None = None) -> Path:
    """``into`` (C1): Ordner eines gelöschten Kapitels – dann erscheint die Szene nicht einzeln im Papierkorb."""
    check_id(scene_id, "scene")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = (into or story_root(project_id) / "trash" / book_id / "scenes") / f"{scene_id}-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    meta_path, text_path = inside(book_dir, "scenes", f"{scene_id}.json"), inside(book_dir, "scenes", f"{scene_id}.md")
    meta = read_json(meta_path) if meta_path.is_file() else {}
    text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""
    write_json(target / "place.json", {**(place or {"chapter_id": "", "chapter_title": "", "after": ""}),
                                       "title": meta.get("title", ""), "words": _words(text),
                                       "deleted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    moves = [(inside(book_dir, "scenes", f"{scene_id}.md"), target / f"{scene_id}.md"),
             (inside(book_dir, "scenes", f"{scene_id}.json"), target / f"{scene_id}.json"),
             (inside(book_dir, "snapshots", scene_id), target / "snapshots"),
             (inside(book_dir, "proposals", f"{scene_id}.md"), target / "proposal.md"),
             (inside(book_dir, "proposals", f"{scene_id}.json"), target / "proposal.json"),
             (inside(book_dir, "proposals", f"{scene_id}.meta.json"), target / "proposal.info.json"),
             *((d, target / "history" / kind) for kind, d in scene_dirs(book_dir, scene_id).items())]
    (target / "history").mkdir()
    for src, dst in moves:
        if src.exists():
            shutil.move(str(src), str(dst))
    return target
