"""Ghostwriter G4c – Steckbrief-Vorschläge (neu oder ändern), Spec §11.5.

Ablage ``proposals/entities/<vorschlag-id>.json``. Steckbriefe liegen in ``structure.json`` (eine Version mit der
Gliederung); übernommen wird erst durch den Autor: unter der Sperre des Buchs, mit Versionsprüfung der Struktur und
derselben Prüfung wie beim Speichern der Struktur. Ändern: nur vorgeschlagene Felder; die Art bleibt.
"""
from __future__ import annotations

from typing import Any

from . import _structure
from ._book import Conflict, _existing, _now, save_structure
from ._files import StoryError, check_id, inside, new_id, read_json, write_json
from ._locks import locked
from .proposals import SOURCES

MAX_NEW = 50
_CHANGE_KEYS = ("name", "aliases", "description", "fields")


def _dir(project_id: str, book_id: str):
    return _existing(project_id, book_id) / "proposals" / "entities"


def _path(project_id: str, book_id: str, proposal_id: str):
    d = _dir(project_id, book_id)
    return inside(d, f"{check_id(proposal_id, 'proposal')}.json")


def _names(e: dict) -> set[str]:
    return {n.strip().lower() for n in [e["name"], *e.get("aliases", [])] if n.strip()}


def _clean(kind: str, changes: dict[str, Any], base: dict | None) -> dict:
    """Vorgeschlagene Felder mit derselben Prüfung wie gespeicherte Steckbriefe; Rückgabe: nur die Felder."""
    merged = {**(base or {"id": "0" * 32, "kind": kind, "name": "", "aliases": [], "description": "", "fields": []}),
              **{k: changes[k] for k in _CHANGE_KEYS if k in changes}}
    try:
        clean = _structure._entity({**merged, "kind": kind})
    except StoryError as exc:
        raise StoryError("entity_invalid") from exc
    return {k: clean[k] for k in _CHANGE_KEYS if k in changes}


def list_for_book(project_id: str, book_id: str) -> list[dict]:
    d = _dir(project_id, book_id)
    out = [read_json(p) for p in d.glob("*.json")] if d.is_dir() else []
    # Reihenfolge des Ablegens: seq (ab 0.10.0) – „at“ ist nur sekundengenau; ältere ohne seq zuerst nach Zeit.
    return sorted(out, key=lambda p: (p.get("seq", 0), p["at"]))


def get(project_id: str, book_id: str, proposal_id: str) -> dict:
    path = _path(project_id, book_id, proposal_id)
    if not path.is_file():
        raise StoryError("proposal_not_found", 404)
    return read_json(path)


@locked
def store(project_id: str, book_id: str, entity_id: str | None, changes: dict[str, Any], *, source: str = "agent",
          session_id: str = "", note: str = "") -> dict:
    if source not in SOURCES:
        raise StoryError("source_invalid")
    st = read_json(_existing(project_id, book_id) / "structure.json")
    entities = st.get("entities", [])
    open_props = list_for_book(project_id, book_id)
    if entity_id:
        base = next((e for e in entities if e["id"] == check_id(entity_id, "entity")), None)
        if base is None:
            raise StoryError("entity_not_found", 404)
        clean = _clean(base["kind"], changes, base)
        diff = {k: v for k, v in clean.items() if v != base[k]}
        if not diff:
            raise StoryError("nothing_changed")
        kind, replaced = base["kind"], [p for p in open_props if p["entity_id"] == entity_id]
    else:
        kind = changes.get("kind")   # Art und Name prüft _clean (wie gespeicherte Steckbriefe; Name ist dort Pflicht)
        diff = _clean(kind, changes, None)
        taken = next((e for e in entities if _names(e) & _names({"name": diff["name"], "aliases": diff.get("aliases", [])})), None)
        if taken:
            raise StoryError("entity_exists", 409, {"entity_id": taken["id"], "name": taken["name"]})
        if sum(1 for p in open_props if not p["entity_id"]) >= MAX_NEW:
            raise StoryError("too_many_proposals")
        replaced = []
    seq = max((p.get("seq", 0) for p in open_props), default=0) + 1   # unter der Sperre: eindeutig je Buch
    proposal = {"id": new_id(), "seq": seq, "entity_id": entity_id or "", "kind": kind, "changes": diff,
                "base_structure_version": st["version"], "source": source, "session_id": session_id, "note": note,
                "at": _now()}
    write_json(_path(project_id, book_id, proposal["id"]), proposal)
    for old in replaced:   # höchstens ein offener Änderungsvorschlag je Steckbrief
        _path(project_id, book_id, old["id"]).unlink(missing_ok=True)
    return proposal


@locked
def discard(project_id: str, book_id: str, proposal_id: str) -> None:
    _path(project_id, book_id, proposal_id).unlink(missing_ok=True)


@locked
def accept(project_id: str, book_id: str, proposal_id: str, base_version: int) -> dict:
    """Steckbrief anlegen bzw. ändern. Gibt die neue Struktur zurück."""
    p = get(project_id, book_id, proposal_id)
    d = _existing(project_id, book_id)
    st = read_json(d / "structure.json")
    if st["version"] != base_version:
        raise Conflict(st)
    entities = [dict(e) for e in st.get("entities", [])]
    if p["entity_id"]:
        target = next((e for e in entities if e["id"] == p["entity_id"]), None)
        if target is None:
            raise StoryError("entity_not_found", 404)
        target.update(p["changes"])
    else:
        entities.append({"id": new_id(), "kind": p["kind"], "name": "", "aliases": [], "description": "", "fields": [],
                         **p["changes"]})
    saved = save_structure(project_id, book_id, {**st, "entities": entities}, base_version=base_version)
    _path(project_id, book_id, proposal_id).unlink(missing_ok=True)
    return saved
