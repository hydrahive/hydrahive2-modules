"""Datei-Ablage für hochgeladene MP3s.

Tracks liegen unter data_dir/modules/musicplayer/. Der Speichername ist eine
UUID (kein Original-Name) — damit ist Pfad-Traversal über den Dateinamen
ausgeschlossen. Das Original landet nur als Anzeige-Titel in der DB.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from hydrahive.settings import settings

MAX_BYTES = 30 * 1024 * 1024  # 30 MB pro Track
_ALLOWED_SUFFIX = ".mp3"
_ALLOWED_MIME = {"audio/mpeg", "audio/mp3"}


def storage_dir() -> Path:
    d = settings.data_dir / "modules" / "musicplayer"
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_allowed_upload(filename: str, content_type: str | None) -> bool:
    name_ok = filename.lower().endswith(_ALLOWED_SUFFIX)
    mime_ok = content_type is None or content_type.lower() in _ALLOWED_MIME
    return name_ok and mime_ok


def save_bytes(data: bytes) -> str:
    """Schreibt die Daten unter einem frischen UUID-Namen, gibt den Namen zurück."""
    name = f"{uuid.uuid4().hex}.mp3"
    (storage_dir() / name).write_bytes(data)
    return name


def file_path(filename: str) -> Path | None:
    """Pfad zu einem gespeicherten Track. None, wenn der Name verdächtig ist."""
    # Defensive: nur reine Dateinamen erlauben (kein Slash, kein '..').
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    p = storage_dir() / filename
    return p if p.is_file() else None


def delete_file(filename: str) -> None:
    p = file_path(filename)
    if p is not None:
        p.unlink(missing_ok=True)
