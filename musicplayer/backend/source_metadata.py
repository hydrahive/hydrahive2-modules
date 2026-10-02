"""Begrenztes Lesen und Normalisieren optionaler Atelier-Sidecars."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

_MAX_SIDECAR_BYTES = 64 * 1024
_META_KEYS = ("prompt", "model", "duration", "created_at")


def _read(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_SIDECAR_BYTES:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def trimmed(sidecar: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for key in _META_KEYS:
        value = sidecar.get(key)
        if key == "duration" and isinstance(value, (int, float)) and not isinstance(value, bool):
            meta[key] = value
        elif key != "duration" and isinstance(value, str) and value:
            limit = 1400 if key == "prompt" else 250
            meta[key] = value.encode("utf-8")[:limit].decode("utf-8", errors="ignore")
    return meta


def load(directory: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Indiziert direkte JSON-Sidecars nach Eigenname und referenzierter Mediendatei."""
    by_stem: dict[str, dict] = {}
    by_filename: dict[str, dict] = {}
    try:
        paths = directory.glob("*.json")
        for path in paths:
            value = _read(path)
            if value is None:
                continue
            by_stem[path.stem] = value
            for key in ("audio_rel", "video_rel", "film_rel"):
                relative = value.get(key)
                if isinstance(relative, str):
                    by_filename[PurePosixPath(relative).name] = value
    except OSError:
        pass
    return by_stem, by_filename
