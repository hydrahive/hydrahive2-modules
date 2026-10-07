"""Hinweise und Notizen des Schreib-Teams am Buch (Spec schreib-team.md §5, Plan T1d).

Ablage ``storyteller/books/<id>/notes/<note-id>.json`` – eine Datei je Eintrag. ``hint`` = Befund an einer Stelle
(Widerspruch, Stil, Plot-Loch), ``note`` = Wissen fürs Buch (Recherche mit Quellen, Ideen). Der Mensch hakt ab
(``done``) oder verwirft (``dismissed``); nichts davon ändert das Buch selbst. Anlegen und Ändern unter der Sperre des
Buchs; ``seq`` hält die Reihenfolge des Ablegens (``at`` ist nur sekundengenau).
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from ._book import _existing, _now, get_structure
from ._files import StoryError, check_id, inside, new_id, read_json, write_json
from ._locks import locked

KINDS = ("hint", "note")
STATUSES = ("open", "done", "dismissed")
MAX_OPEN = 500
MAX_SOURCES = 10
_LIMITS = {"title": 200, "text": 4000, "author": 200, "agent_id": 64, "session_id": 64}


def _dir(project_id: str, book_id: str):
    return _existing(project_id, book_id) / "notes"


def _path(project_id: str, book_id: str, note_id: str):
    return inside(_dir(project_id, book_id), f"{check_id(note_id, 'note')}.json")


def _sources(raw: Any) -> list[dict]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list) or len(raw) > MAX_SOURCES:
        raise StoryError("note_invalid")
    out = []
    for s in raw:
        url = str((s or {}).get("url") or "") if isinstance(s, dict) else ""
        if urlparse(url).scheme not in ("http", "https") or len(url) > 2000:
            raise StoryError("note_invalid")
        out.append({"title": str(s.get("title") or "")[:200], "url": url})
    return out


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("kind") not in KINDS:
        raise StoryError("note_invalid")
    out: dict[str, Any] = {"kind": data["kind"]}
    for key, limit in _LIMITS.items():
        value = str(data.get(key) or "").strip()
        if len(value) > limit or (key in ("title", "text") and not value):
            raise StoryError("note_invalid")
        out[key] = value
    out["sources"] = _sources(data.get("sources"))
    return out


def _place(project_id: str, book_id: str, data: dict[str, Any]) -> dict[str, str]:
    """Stelle (Szene/Kapitel/Steckbrief) – optional, muss aber existieren."""
    st = get_structure(project_id, book_id)
    chapters = {c["id"]: c for p in st["parts"] for c in p["chapters"]}
    known = {"scene_id": {s for c in chapters.values() for s in c["scenes"]}, "chapter_id": set(chapters),
             "entity_id": {e["id"] for e in st.get("entities", [])}}
    out = {}
    for key, ids in known.items():
        value = data.get(key)
        if value:
            if value not in ids:
                raise StoryError("place_not_found")
            out[key] = value
    return out


def _all(project_id: str, book_id: str) -> list[dict]:
    d = _dir(project_id, book_id)
    return sorted((read_json(p) for p in d.glob("*.json")), key=lambda n: n["seq"]) if d.is_dir() else []


@locked
def add(project_id: str, book_id: str, data: dict[str, Any]) -> dict:
    clean, place = _clean(data), _place(project_id, book_id, data)
    existing = _all(project_id, book_id)
    if sum(1 for n in existing if n["status"] == "open") >= MAX_OPEN:
        raise StoryError("too_many_notes")
    now = _now()
    note = {"id": new_id(), "seq": max((n["seq"] for n in existing), default=0) + 1, **clean, **place,
            "status": "open", "at": now, "updated_at": now}
    write_json(inside(_dir(project_id, book_id), f"{note['id']}.json"), note)
    return note


def list_notes(project_id: str, book_id: str, *, status: str = "open", scene_id: str | None = None) -> list[dict]:
    notes = _all(project_id, book_id)
    if status != "all":
        notes = [n for n in notes if n["status"] == status]
    if scene_id:
        notes = [n for n in notes if n.get("scene_id") == scene_id]
    return notes


def open_counts(project_id: str, book_id: str) -> dict[str, int]:
    """Offene Einträge je Szene (für den Punkt im Navigator)."""
    out: dict[str, int] = {}
    for n in _all(project_id, book_id):
        if n["status"] == "open" and n.get("scene_id"):
            out[n["scene_id"]] = out.get(n["scene_id"], 0) + 1
    return out


@locked
def set_status(project_id: str, book_id: str, note_id: str, status: str) -> dict:
    if status not in STATUSES:
        raise StoryError("status_invalid")
    path = _path(project_id, book_id, note_id)
    if not path.is_file():
        raise StoryError("note_not_found", 404)
    note = {**read_json(path), "status": status, "updated_at": _now()}
    write_json(path, note)
    return note


@locked
def delete(project_id: str, book_id: str, note_id: str) -> None:
    path = _path(project_id, book_id, note_id)
    if not path.is_file():
        raise StoryError("note_not_found", 404)
    path.unlink()
