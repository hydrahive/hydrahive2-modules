"""Atelier — Sound-Profile & Musik-CI (dateibasiert im Projekt-Workspace).

Ein Sound-Profil ist ein wiederverwendbarer Track-Anker: Name + Beschreibung
(Genre/Mood/Instrumente/BPM, verbatim in jeden Musik-Prompt), optional ein
Ziel-Modell. Gespeichert als ``audio/profiles/<id>/profile.json``. Kein
Bild/Seed/Palette — eigenständiges, schlankeres Datenmodell als Charaktere.

Der Studio-Sound-Anker (``music_style_anchor``) liegt im bestehenden CI-Kit
(``ci.json``), Feld wird hier nur gelesen/geschrieben — siehe ``characters.py``.
"""
from __future__ import annotations

import json
from typing import Any

from . import storage


def _read_json(path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def get_music_anchor(project_id: str) -> str:
    """Studio-Sound-Anker aus dem bestehenden CI-Kit (leer wenn nicht gesetzt)."""
    ci = _read_json(storage.atelier_root(project_id) / "ci.json", {})
    return str(ci.get("music_style_anchor") or "")


def save_music_anchor(project_id: str, anchor: str) -> str:
    ci_path = storage.atelier_root(project_id) / "ci.json"
    ci = _read_json(ci_path, {})
    ci["music_style_anchor"] = str(anchor or "")[:2000]
    _write_json(ci_path, ci)
    return ci["music_style_anchor"]


def list_profiles(project_id: str) -> list[dict]:
    out: list[dict] = []
    pdir = storage.audio_profiles_dir(project_id)
    for child in sorted(pdir.iterdir()) if pdir.is_dir() else []:
        if not child.is_dir():
            continue
        data = _read_json(child / "profile.json", None)
        if isinstance(data, dict):
            out.append(data)
    return out


def get_profile(project_id: str, profile_id: str) -> dict | None:
    if not storage.is_valid_id(profile_id):
        return None
    data = _read_json(
        storage.audio_profiles_dir(project_id) / profile_id / "profile.json", None
    )
    return data if isinstance(data, dict) else None


def _sanitize(profile_id: str, data: dict) -> dict:
    return {
        "id": profile_id,
        "name": str(data.get("name") or "")[:200],
        "description": str(data.get("description") or "")[:2000],
        "model": str(data.get("model") or "")[:200],
    }


def create_profile(project_id: str, data: dict) -> dict:
    profile_id = storage.new_id()
    profile = _sanitize(profile_id, data)
    pdir = storage.audio_profiles_dir(project_id) / profile_id
    pdir.mkdir(parents=True, exist_ok=True)
    _write_json(pdir / "profile.json", profile)
    return profile


def update_profile(project_id: str, profile_id: str, data: dict) -> dict | None:
    existing = get_profile(project_id, profile_id)
    if existing is None:
        return None
    merged = {**existing, **data}
    profile = _sanitize(profile_id, merged)
    _write_json(
        storage.audio_profiles_dir(project_id) / profile_id / "profile.json", profile
    )
    return profile


def delete_profile(project_id: str, profile_id: str) -> bool:
    if not storage.is_valid_id(profile_id):
        return False
    pdir = storage.audio_profiles_dir(project_id) / profile_id
    if not pdir.is_dir():
        return False
    for f in pdir.iterdir():
        f.unlink(missing_ok=True)
    pdir.rmdir()
    return True
