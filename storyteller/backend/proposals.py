"""Ghostwriter G2 – abgelegte Vorschläge (Spec ghostwriter.md §9.3).

Hatte eine Szene beim Lauf schon Text oder wurde sie inzwischen geändert, schreibt der Lauf NICHT in die
Szene, sondern legt den Text hier ab: ``proposals/<szene>.md`` + ``.json`` (Lauf, Modell, Basisversion).
Erst „Übernehmen“ setzt ihn ein – mit Schnappschuss des alten Texts und Versionsprüfung.
Ersetzen und Verwerfen löschen nie: der alte Vorschlag wandert in den Verlauf (``_replaced``, A2) und lässt sich
zurückholen.
"""
from __future__ import annotations

from . import _replaced
from ._book import MAX_SCENE_BYTES, Conflict, _existing, _now
from ._files import StoryError, check_id, inside, read_json, write_atomic, write_json
from ._locks import locked
from .scenes import get_scene, save_scene
from .snapshots import add_snapshot


def _paths(project_id: str, book_id: str, scene_id: str):
    d = _existing(project_id, book_id)
    check_id(scene_id, "scene")
    if not inside(d, "scenes", f"{scene_id}.json").is_file():
        raise StoryError("scene_not_found", 404)
    return inside(d, "proposals", f"{scene_id}.json"), inside(d, "proposals", f"{scene_id}.md")


def _words(text: str) -> int:
    return sum(1 for w in text.split() if any(c.isalnum() for c in w))


SOURCES = ("run", "agent")
_DEFAULTS = {"source": "run", "session_id": "", "note": "", "scene_words": 0, "author": "", "replaced_from": None}   # ältere ohne diese Felder
RUN_AUTHOR = "Ghostwriter-Lauf"


def origin_of(p: dict) -> str:
    """Wer den Vorschlag abgelegt hat – für „ersetzt einen Vorschlag von …“."""
    return p.get("author") or (RUN_AUTHOR if p.get("source", "run") == "run" else "Agent")


def _current(meta_path, text_path) -> tuple[dict, str] | None:
    if not meta_path.is_file() or not text_path.is_file():
        return None
    return {**_DEFAULTS, **read_json(meta_path)}, text_path.read_text(encoding="utf-8")


def _to_history(project_id: str, book_id: str, scene_id: str, meta_path, text_path, *, reason: str, by: str) -> dict | None:
    """Offenen Vorschlag in den Verlauf legen und entfernen. Gibt seine Meta zurück (oder None)."""
    cur = _current(meta_path, text_path)
    if cur is None:
        return None
    _replaced.keep(project_id, book_id, "text", scene_id, cur[0], text=cur[1], reason=reason, by=by)
    meta_path.unlink(missing_ok=True)
    text_path.unlink(missing_ok=True)
    return cur[0]


@locked
def store(project_id: str, book_id: str, scene_id: str, text: str, *, run_id: str, model: str,
          base_version: int, source: str = "run", session_id: str = "", note: str = "", scene_words: int = 0,
          author: str = "") -> dict:
    """Vorschlag ablegen. Ein älterer wandert in den Verlauf (``replaced_from`` sagt, von wem er war).
    Die Szene selbst wird nicht angefasst.
    ``source``: run (Ghostwriter-Lauf) | agent (Agent im Chat, mit ``session_id``).
    ``scene_words``: Wortzahl der Szene beim Ablegen – die Oberfläche warnt, wenn der Vorschlag viel kürzer ist."""
    meta_path, text_path = _paths(project_id, book_id, scene_id)
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_SCENE_BYTES:
        raise StoryError("text_too_long")
    if source not in SOURCES:
        raise StoryError("source_invalid")
    meta = {"scene_id": scene_id, "run_id": run_id, "model": model, "base_version": base_version,
            "words": _words(text), "at": _now(), "source": source, "session_id": session_id, "note": note,
            "scene_words": scene_words, "author": (author or (RUN_AUTHOR if source == "run" else ""))[:200]}
    old = _to_history(project_id, book_id, scene_id, meta_path, text_path, reason="replaced", by=origin_of(meta))
    replaced_from = {"source": old["source"], "author": origin_of(old), "at": old["at"]} if old else None
    meta["replaced_from"] = replaced_from       # Hinweis „ersetzt einen Vorschlag von …“ in der Oberfläche
    write_atomic(text_path, text)
    write_json(meta_path, meta)
    return meta


def get(project_id: str, book_id: str, scene_id: str) -> dict:
    meta_path, text_path = _paths(project_id, book_id, scene_id)
    if not meta_path.is_file() or not text_path.is_file():
        raise StoryError("proposal_not_found", 404)
    return {**_DEFAULTS, **read_json(meta_path), "text": text_path.read_text(encoding="utf-8")}


def list_for_book(project_id: str, book_id: str) -> list[dict]:
    """Kurzinfos aller offenen Vorschläge (ohne Text)."""
    d = _existing(project_id, book_id) / "proposals"
    out = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        if p.name.endswith(".meta.json") or p.name == "outline.json":   # Szenen-Infos (G4b), Gliederung (G4d)
            continue
        if p.with_suffix(".md").is_file():
            out.append({**_DEFAULTS, **read_json(p)})   # ältere ohne Herkunft
    return out


@locked
def discard(project_id: str, book_id: str, scene_id: str) -> None:
    """Verwerfen = in den Verlauf (zurückholbar)."""
    meta_path, text_path = _paths(project_id, book_id, scene_id)
    _to_history(project_id, book_id, scene_id, meta_path, text_path, reason="discarded", by="")


@locked
def restore(project_id: str, book_id: str, scene_id: str, entry_id: str) -> dict:
    """Eintrag aus dem Verlauf wieder zum offenen Vorschlag machen; ein gerade offener wandert in den Verlauf."""
    meta_path, text_path = _paths(project_id, book_id, scene_id)
    entry = _replaced.take(project_id, book_id, "text", scene_id, entry_id)
    _to_history(project_id, book_id, scene_id, meta_path, text_path, reason="restored_over", by="")
    write_atomic(text_path, entry["text"])
    write_json(meta_path, entry["proposal"])
    return {**_DEFAULTS, **entry["proposal"], "text": entry["text"]}


@locked
def accept(project_id: str, book_id: str, scene_id: str, base_version: int) -> dict:
    """Vorschlag einsetzen: Versionsprüfung (der Autor muss den aktuellen Stand kennen), Schnappschuss
    des bisherigen Texts, Text + Herkunft „KI-Entwurf“, dann Vorschlag löschen."""
    proposal = get(project_id, book_id, scene_id)
    current = get_scene(project_id, book_id, scene_id)
    if current["version"] != base_version:
        raise Conflict(current)
    if current["text"].strip():
        add_snapshot(project_id, book_id, scene_id, current["text"])
    saved = save_scene(project_id, book_id, scene_id, {"text": proposal["text"], "origin": "ai_draft"},
                       base_version=base_version)
    for p in _paths(project_id, book_id, scene_id):   # übernommen: steht jetzt in der Szene, nicht in den Verlauf
        p.unlink(missing_ok=True)
    return saved
