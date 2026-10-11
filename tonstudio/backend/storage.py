"""Tonstudio — Ablage im Projekt-Workspace (SPEC.md §4).

    <workspace>/tonstudio/
      songs/<song_id>/song.json, lyrics.md, versions/<n>.json, exports/
      trash/<song_id>/           gelöschte Songs (wiederherstellbar)
      clips/<clip_id>.<ext>      erzeugte oder hochgeladene Quellen (unveränderlich)
      clips/<clip_id>.json       Sidecar (Herkunft, Dauer)

Zugriff nur für Projektmitglieder (``user_can_access``). Jeder Pfad wird gegen den Workspace geprüft
(``safe_under``: resolve + relative_to), damit nichts aus dem Projekt herausführt. Muster wie atelier/storage.py.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from hydrahive.projects._config_io import list_for_user
from hydrahive.projects._paths import ensure_workspace

_ID_RE = re.compile(r"^[a-f0-9]{32}$")
_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")

AUDIO_EXT = ("mp3", "wav", "flac", "ogg", "m4a", "aac", "opus")
MAX_UPLOAD_BYTES = 100 * 1024 * 1024          # 100 MB je Datei (SPEC §8)


def is_project_id(value: str) -> bool:
    return bool(_PROJECT_ID_RE.match(value or ""))


def user_can_access(username: str, project_id: str) -> bool:
    return any(p.get("id") == project_id for p in list_for_user(username))


def new_id() -> str:
    return uuid.uuid4().hex


def is_valid_id(value: str) -> bool:
    return bool(_ID_RE.match(value or ""))


def workspace_root(project_id: str) -> Path:
    return ensure_workspace(project_id)


def _sub(project_id: str, *parts: str) -> Path:
    d = workspace_root(project_id).joinpath("tonstudio", *parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def tonstudio_root(project_id: str) -> Path:
    return _sub(project_id)


def songs_dir(project_id: str) -> Path:
    return _sub(project_id, "songs")


def trash_dir(project_id: str) -> Path:
    return _sub(project_id, "trash")


def clips_dir(project_id: str) -> Path:
    return _sub(project_id, "clips")


def safe_under(root: Path, rel: str) -> Path | None:
    """``rel`` unterhalb von ``root`` auflösen. None bei absolutem Pfad oder Ausbruch."""
    if not rel or rel.startswith("/") or "\x00" in rel:
        return None
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def rel_to_workspace(project_id: str, path: Path) -> str:
    return str(path.resolve().relative_to(workspace_root(project_id)))


def audio_ext(filename: str) -> str | None:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext if ext in AUDIO_EXT else None
