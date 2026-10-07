"""Ghostwriter G4b – Vorschläge für Szenen-Infos (Titel, Zusammenfassung, Perspektive), Spec §11.5.

Ablage ``proposals/<szene>.meta.json`` – getrennt vom Text-Vorschlag (``<szene>.md/.json``), beide können
gleichzeitig offen sein. Die Szene wird erst beim Übernehmen geändert (Versionsprüfung, Feldauswahl); die
Herkunft des Szenentexts bleibt dabei unverändert. Alle Änderungen unter der Sperre des Buchs.
"""
from __future__ import annotations

from ._book import Conflict, _existing, _now
from ._files import StoryError, check_id, inside, read_json, write_json
from ._locks import locked
from .proposals import SOURCES
from .scenes import get_scene, save_scene

FIELDS = {"title": 200, "summary": 2000, "pov": 200}


def _path(project_id: str, book_id: str, scene_id: str):
    d = _existing(project_id, book_id)
    check_id(scene_id, "scene")
    if not inside(d, "scenes", f"{scene_id}.json").is_file():
        raise StoryError("scene_not_found", 404)
    return inside(d, "proposals", f"{scene_id}.meta.json")


@locked
def store(project_id: str, book_id: str, scene_id: str, fields: dict, *, base_version: int, source: str = "agent",
          session_id: str = "", note: str = "") -> dict:
    """Vorschlag ablegen (ersetzt einen älteren). Nur Felder, die sich vom aktuellen Stand unterscheiden."""
    path = _path(project_id, book_id, scene_id)
    if source not in SOURCES:
        raise StoryError("source_invalid")
    current = get_scene(project_id, book_id, scene_id)
    changed = {}
    for key, limit in FIELDS.items():
        if key not in fields or fields[key] is None:
            continue
        value = fields[key]
        if not isinstance(value, str) or len(value) > limit:
            raise StoryError(f"{key}_invalid")
        if value.strip() != current[key].strip():
            changed[key] = value.strip()
    if not changed:
        raise StoryError("nothing_changed")
    info = {"scene_id": scene_id, "kind": "info", "fields": changed, "base_version": base_version, "source": source,
            "session_id": session_id, "note": note, "at": _now()}
    write_json(path, info)
    return info


def get(project_id: str, book_id: str, scene_id: str) -> dict:
    path = _path(project_id, book_id, scene_id)
    if not path.is_file():
        raise StoryError("proposal_not_found", 404)
    return read_json(path)


def list_for_book(project_id: str, book_id: str) -> list[dict]:
    d = _existing(project_id, book_id) / "proposals"
    return [read_json(p) for p in sorted(d.glob("*.meta.json"))] if d.is_dir() else []


@locked
def discard(project_id: str, book_id: str, scene_id: str) -> None:
    _path(project_id, book_id, scene_id).unlink(missing_ok=True)


@locked
def accept(project_id: str, book_id: str, scene_id: str, base_version: int, fields: list[str] | None = None) -> dict:
    """Gewählte Felder (Standard: alle) übernehmen. Versionsprüfung: der Autor muss den aktuellen Stand kennen."""
    proposal = get(project_id, book_id, scene_id)
    chosen = list(proposal["fields"]) if fields is None else fields
    if not chosen or any(f not in proposal["fields"] for f in chosen):
        raise StoryError("fields_invalid")
    current = get_scene(project_id, book_id, scene_id)
    if current["version"] != base_version:
        raise Conflict(current)
    saved = save_scene(project_id, book_id, scene_id, {k: proposal["fields"][k] for k in chosen}, base_version=base_version)
    _path(project_id, book_id, scene_id).unlink(missing_ok=True)
    return saved
