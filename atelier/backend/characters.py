"""Atelier — Charaktere & CI-Kit (dateibasiert im Projekt-Workspace).

Ein Charakter ist eine wiederverwendbare Figur mit Steckbrief, Style-Anchor,
Palette, optionalem Seed/Modell und Hero-Referenzbildern. Gespeichert als
``characters/<id>/character.json``. Das CI-Kit (``ci.json``) hält den
projektweiten Stil-Anker, die Palette und das Default-Modell.

Bewusst dateibasiert (kein DB-Schema): bleibt beim Projekt, einfach zu
sichern/exportieren, kein Migrations-Overhead.
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


# ---- CI-Kit -----------------------------------------------------------------

def get_ci(project_id: str) -> dict:
    ci = _read_json(storage.atelier_root(project_id) / "ci.json", {})
    ci.setdefault("palette", [])
    ci.setdefault("style_anchor", "")
    ci.setdefault("default_model", "")
    ci.setdefault("aspect_ratio", "1:1")
    return ci


def save_ci(project_id: str, data: dict) -> dict:
    ci = {
        "palette": [str(c) for c in (data.get("palette") or [])][:12],
        "style_anchor": str(data.get("style_anchor") or "")[:2000],
        "default_model": str(data.get("default_model") or "")[:200],
        "aspect_ratio": str(data.get("aspect_ratio") or "1:1")[:16],
    }
    _write_json(storage.atelier_root(project_id) / "ci.json", ci)
    return ci


# ---- Charaktere -------------------------------------------------------------

def list_characters(project_id: str) -> list[dict]:
    out: list[dict] = []
    cdir = storage.characters_dir(project_id)
    for child in sorted(cdir.iterdir()) if cdir.is_dir() else []:
        if not child.is_dir():
            continue
        data = _read_json(child / "character.json", None)
        if isinstance(data, dict):
            out.append(data)
    return out


def get_character(project_id: str, char_id: str) -> dict | None:
    if not storage.is_valid_id(char_id):
        return None
    data = _read_json(
        storage.characters_dir(project_id) / char_id / "character.json", None
    )
    return data if isinstance(data, dict) else None


def _sanitize(char_id: str, data: dict) -> dict:
    return {
        "id": char_id,
        "name": str(data.get("name") or "")[:200],
        "description": str(data.get("description") or "")[:4000],
        "style_anchor": str(data.get("style_anchor") or "")[:2000],
        "palette": [str(c) for c in (data.get("palette") or [])][:12],
        "seed": data.get("seed") if isinstance(data.get("seed"), int) else None,
        "model": str(data.get("model") or "")[:200],
        "references": [str(r) for r in (data.get("references") or [])][:8],
    }


def create_character(project_id: str, data: dict) -> dict:
    char_id = storage.new_id()
    char = _sanitize(char_id, data)
    cdir = storage.characters_dir(project_id) / char_id
    cdir.mkdir(parents=True, exist_ok=True)
    _write_json(cdir / "character.json", char)
    return char


def update_character(project_id: str, char_id: str, data: dict) -> dict | None:
    existing = get_character(project_id, char_id)
    if existing is None:
        return None
    merged = {**existing, **data}
    char = _sanitize(char_id, merged)
    _write_json(
        storage.characters_dir(project_id) / char_id / "character.json", char
    )
    return char


def add_reference(project_id: str, char_id: str, rel_path: str) -> dict | None:
    char = get_character(project_id, char_id)
    if char is None:
        return None
    refs = list(char.get("references") or [])
    if rel_path not in refs:
        refs.append(rel_path)
    char["references"] = refs[:8]
    _write_json(
        storage.characters_dir(project_id) / char_id / "character.json", char
    )
    return char


def delete_character(project_id: str, char_id: str) -> bool:
    if not storage.is_valid_id(char_id):
        return False
    cdir = storage.characters_dir(project_id) / char_id
    if not cdir.is_dir():
        return False
    for f in cdir.iterdir():
        f.unlink(missing_ok=True)
    cdir.rmdir()
    return True
