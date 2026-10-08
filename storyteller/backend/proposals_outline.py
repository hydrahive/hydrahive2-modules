"""Ghostwriter G4d – Gliederungs-Vorschlag des Agenten (neue Kapitel/Szenen), Spec §11.5.

Genau ein offener Vorschlag je Buch: ``proposals/outline.json`` (ersetzt einen älteren). Übernommen wird die
Fassung, die der Autor in der Oberfläche (ggf. bearbeitet) zurückschickt – Prüfung und Einfügen wie „Gliederung
aus Idee“ (G2: ``outline.validate`` + ``outline.apply``: anhängen bzw. leere Start-Szene ersetzen, Steckbriefe nur
für neue Namen, Versionsprüfung). Alles unter der Sperre des Buchs. Ersetzen/Verwerfen → Verlauf (A2).
"""
from __future__ import annotations

from typing import Any

from . import _replaced, outline
from ._book import _existing, _now
from ._files import StoryError, read_json, write_json
from ._locks import locked
from .proposals import SOURCES, origin_of


def _path(project_id: str, book_id: str):
    return _existing(project_id, book_id) / "proposals" / "outline.json"


def get(project_id: str, book_id: str) -> dict:
    path = _path(project_id, book_id)
    if not path.is_file():
        raise StoryError("proposal_not_found", 404)
    return read_json(path)


def find(project_id: str, book_id: str) -> dict | None:
    path = _path(project_id, book_id)
    return read_json(path) if path.is_file() else None


@locked
def store(project_id: str, book_id: str, data: Any, *, source: str = "agent", session_id: str = "", note: str = "",
          author: str = "") -> dict:
    if source not in SOURCES:
        raise StoryError("source_invalid")
    clean = outline.validate(data)
    st = read_json(_existing(project_id, book_id) / "structure.json")
    proposal = {"outline": clean, "base_structure_version": st["version"], "source": source, "session_id": session_id,
                "note": note, "at": _now(), "author": author[:200]}
    old = _to_history(project_id, book_id, reason="replaced", by=origin_of(proposal))
    write_json(_path(project_id, book_id), proposal)
    return {**proposal, "replaced_from": {"source": old.get("source", "agent"), "author": origin_of(old), "at": old["at"]}
            if old else None}


def _to_history(project_id: str, book_id: str, *, reason: str, by: str) -> dict | None:
    path = _path(project_id, book_id)
    if not path.is_file():
        return None
    old = read_json(path)
    _replaced.keep(project_id, book_id, "outline", "outline", old, reason=reason, by=by)
    path.unlink()
    return old


@locked
def discard(project_id: str, book_id: str) -> None:
    """Verwerfen = in den Verlauf (zurückholbar)."""
    _to_history(project_id, book_id, reason="discarded", by="")


@locked
def restore(project_id: str, book_id: str, entry_id: str) -> dict:
    entry = _replaced.take(project_id, book_id, "outline", "outline", entry_id)
    _to_history(project_id, book_id, reason="replaced", by="zurückgeholt")
    write_json(_path(project_id, book_id), entry["proposal"])
    return entry["proposal"]


@locked
def accept(project_id: str, book_id: str, edited: Any, base_version: int) -> dict:
    """Die (bearbeitete) Fassung einfügen. Fehler (Konflikt, ungültig, zu viele Szenen) → Vorschlag bleibt."""
    get(project_id, book_id)   # ohne offenen Vorschlag nichts einfügen
    result = outline.apply(project_id, book_id, edited, base_version)
    _path(project_id, book_id).unlink(missing_ok=True)
    return result
