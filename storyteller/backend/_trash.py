"""Gelöschte Szenen in den Papierkorb statt endgültig löschen (Fix 0.6.1) – wie ganze Bücher.

    storyteller/trash/<buch>/scenes/<szene>-<zeit>/
        <szene>.md, <szene>.json      Text und Infos
        snapshots/*.md                Schnappschüsse
        proposal.md, proposal.json    offener KI-Vorschlag (falls vorhanden)
        proposal.info.json            offener Vorschlag für Szenen-Infos (G4b)
Wiederherstellen gibt es (noch) nicht in der Oberfläche; die Dateien sind vollständig da.
Aufrufer hält die Sperre des Buchs.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from ._files import check_id, inside, story_root


def trash_scene(project_id: str, book_id: str, book_dir: Path, scene_id: str) -> Path:
    check_id(scene_id, "scene")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    target = story_root(project_id) / "trash" / book_id / "scenes" / f"{scene_id}-{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    moves = [(inside(book_dir, "scenes", f"{scene_id}.md"), target / f"{scene_id}.md"),
             (inside(book_dir, "scenes", f"{scene_id}.json"), target / f"{scene_id}.json"),
             (inside(book_dir, "snapshots", scene_id), target / "snapshots"),
             (inside(book_dir, "proposals", f"{scene_id}.md"), target / "proposal.md"),
             (inside(book_dir, "proposals", f"{scene_id}.json"), target / "proposal.json"),
             (inside(book_dir, "proposals", f"{scene_id}.meta.json"), target / "proposal.info.json")]
    for src, dst in moves:
        if src.exists():
            shutil.move(str(src), str(dst))
    return target
