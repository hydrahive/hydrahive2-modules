"""Datei-Ablage für hochgeladene MP3s.

Tracks liegen unter data_dir/modules/musicplayer/. Der Speichername ist eine
UUID (kein Original-Name) — damit ist Pfad-Traversal über den Dateinamen
ausgeschlossen. Das Original landet nur als Anzeige-Titel in der DB.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from hydrahive.settings import settings


def workspaces_root() -> Path:
    """Erlaubter Scan-Root für generierte Musik (= Media-Root in core files.py)."""
    return (settings.data_dir / "workspaces").resolve()


def resolve_in_workspaces(rel_path: str) -> Path | None:
    """Validiert einen relativen Pfad gegen den Workspaces-Root.

    Gibt den absoluten Pfad zurück, wenn er sicher unter dem Root liegt, eine
    .mp3-Datei in einem 'generated'-Ordner ist und existiert — sonst None.
    Schützt gegen Traversal/Symlink-Ausbruch via resolve()+relative_to().
    """
    if not rel_path or rel_path.endswith("/"):
        return None
    root = workspaces_root()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.suffix.lower() != ".mp3":
        return None
    if "generated" not in candidate.parts:
        return None
    return candidate if candidate.is_file() else None


def scan_generated() -> list[Path]:
    """Alle generated/*.mp3 unterhalb des Workspaces-Roots (sortiert, neueste zuerst)."""
    root = workspaces_root()
    if not root.is_dir():
        return []
    files = [p for p in root.glob("*/*/generated/*.mp3") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def copy_into_pool(src: Path) -> str:
    """Kopiert eine Quelldatei in den Pool (neuer UUID-Name). Quelle bleibt."""
    return save_bytes(src.read_bytes())

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
