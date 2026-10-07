"""Schnappschüsse einer Szene als Dateien: snapshots/<scene-id>/<zeit>.md (höchstens MAX_SNAPSHOTS)."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ._book import MAX_SCENE_BYTES, _existing
from ._files import StoryError, check_id, inside, write_atomic
from ._locks import locked

MAX_SNAPSHOTS = 50
_STAMP_RE = re.compile(r"^\d{8}T\d{12}$")


def _dir(project_id: str, book_id: str, scene_id: str):
    d = _existing(project_id, book_id)
    check_id(scene_id, "scene")
    if not inside(d, "scenes", f"{scene_id}.json").is_file():
        raise StoryError("scene_not_found", 404)
    return d, inside(d, "snapshots", scene_id)


@locked
def add_snapshot(project_id: str, book_id: str, scene_id: str, text: str | None = None) -> dict:
    """Stand der Szene sichern – oder ``text`` (z. B. die eigene Fassung bei einem Konflikt)."""
    d, snap_dir = _dir(project_id, book_id, scene_id)
    if text is None:
        text_path = inside(d, "scenes", f"{scene_id}.md")
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_SCENE_BYTES:
        raise StoryError("text_too_long")
    newest = max(snap_dir.glob("*.md"), default=None) if snap_dir.is_dir() else None
    if newest is not None and newest.read_text(encoding="utf-8") == text:
        return _info(newest.stem, text)  # nichts Neues: keinen doppelten Schnappschuss anlegen
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    write_atomic(snap_dir / f"{stamp}.md", text)
    for old in sorted(snap_dir.glob("*.md"), reverse=True)[MAX_SNAPSHOTS:]:
        old.unlink(missing_ok=True)
    return _info(stamp, text)


def list_snapshots(project_id: str, book_id: str, scene_id: str) -> list[dict]:
    """Liste ohne Text (klein halten); den Text liefert ``get_snapshot``."""
    _, snap_dir = _dir(project_id, book_id, scene_id)
    if not snap_dir.is_dir():
        return []
    out = []
    for p in sorted(snap_dir.glob("*.md"), reverse=True):
        info = _info(p.stem, p.read_text(encoding="utf-8"))
        info.pop("text")
        out.append(info)
    return out


def get_snapshot(project_id: str, book_id: str, scene_id: str, snapshot_id: str) -> dict:
    if not isinstance(snapshot_id, str) or not _STAMP_RE.match(snapshot_id):
        raise StoryError("snapshot_not_found", 404)
    _, snap_dir = _dir(project_id, book_id, scene_id)
    path = inside(snap_dir, f"{snapshot_id}.md")
    if not path.is_file():
        raise StoryError("snapshot_not_found", 404)
    return _info(snapshot_id, path.read_text(encoding="utf-8"))


def _info(stamp: str, text: str) -> dict:
    at = datetime.strptime(stamp, "%Y%m%dT%H%M%S%f").replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
    return {"id": stamp, "at": at, "words": sum(1 for w in text.split() if any(c.isalnum() for c in w)), "text": text}
