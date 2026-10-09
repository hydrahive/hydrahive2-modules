"""A5(c) – Kapitel-Zusammenfassung (Spec ki-qualitaet-a5.md §2c).

    storyteller/books/<id>/chapters.json  {<kapitel-id>: {summary, version, updated_at}}

Eigene Datei statt Feld in structure.json: die Oberfläche speichert die Gliederung als Ganzes und würde ein Feld dort
überschreiben. Speichern mit Versionsprüfung je Kapitel. Einträge gelöschter Kapitel bleiben liegen (kein stiller
Datenverlust), werden aber nicht mehr geliefert. ``generate`` baut einen Vorschlag aus den Szenen-Zusammenfassungen des
Kapitels – gespeichert wird erst, was der Autor übernimmt. Nichts wird automatisch erzeugt.
"""
from __future__ import annotations

from hydrahive.llm.client import complete

from . import storage
from ._book import Conflict, _existing, _now
from ._files import StoryError, check_id, read_json, write_json
from ._locks import locked
from ._names import LANGUAGE_LABEL
from ._texts import texts

MAX_SUMMARY = 4000
_FILE = "chapters.json"


def _read(project_id: str, book_id: str) -> dict[str, dict]:
    path = _existing(project_id, book_id) / _FILE
    data = read_json(path) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def _chapter_ids(structure: dict) -> list[str]:
    return [c["id"] for p in structure["parts"] for c in p["chapters"]]


def from_structure(project_id: str, book_id: str, structure: dict) -> dict[str, str]:
    """Kapitel-ID → Zusammenfassung, nur bestehende Kapitel mit Text (für das Gedächtnis)."""
    data = _read(project_id, book_id)
    return {cid: data[cid]["summary"] for cid in _chapter_ids(structure)
            if cid in data and data[cid].get("summary", "").strip()}


def get_all(project_id: str, book_id: str) -> dict[str, dict]:
    st = storage.get_structure(project_id, book_id)
    data = _read(project_id, book_id)
    return {cid: data[cid] for cid in _chapter_ids(st) if cid in data and data[cid].get("summary", "").strip()}


def _current(project_id: str, book_id: str, chapter_id: str) -> dict:
    check_id(chapter_id, "chapter")
    if chapter_id not in _chapter_ids(storage.get_structure(project_id, book_id)):
        raise StoryError("chapter_not_found", 404)
    return _read(project_id, book_id).get(chapter_id) or {"summary": "", "version": 0, "updated_at": ""}


@locked
def save(project_id: str, book_id: str, chapter_id: str, summary: str, base_version: int) -> dict:
    current = _current(project_id, book_id, chapter_id)
    if current["version"] != base_version:
        raise Conflict(current)
    if not isinstance(summary, str) or len(summary) > MAX_SUMMARY:
        raise StoryError("summary_invalid")
    entry = {"summary": summary.strip(), "version": current["version"] + 1, "updated_at": _now()}
    data = _read(project_id, book_id)
    data[chapter_id] = entry
    write_json(_existing(project_id, book_id) / _FILE, data)
    return entry


async def generate(project_id: str, book_id: str, chapter_id: str, *, model: str | None) -> dict:
    """Vorschlag aus den Szenen-Zusammenfassungen des Kapitels (keine Szenentexte). Speichert nichts."""
    from .ai import clean_proposal
    from .ghost import choose_model
    check_id(chapter_id, "chapter")
    book = storage.get_book(project_id, book_id)
    st = storage.get_structure(project_id, book_id)
    ch = next((c for p in st["parts"] for c in p["chapters"] if c["id"] == chapter_id), None)
    if ch is None:
        raise StoryError("chapter_not_found", 404)
    infos = [storage.scene_info(project_id, book_id, s) for s in ch["scenes"]]
    lines = "\n".join(f"- {i['title']}: {i['summary']}" for i in infos if i["summary"].strip())
    if not lines:
        raise StoryError("summaries_required")
    t = texts(book)
    raw = await complete([
        {"role": "system", "content": t("summarize_chapter", lang=LANGUAGE_LABEL.get(book["language"], book["language"]))},
        {"role": "user", "content": t("chapter_input", title=ch["title"], lines=lines)},
    ], model=choose_model(book, model), temperature=0.2, max_tokens=600)
    summary = clean_proposal(raw or "")[:MAX_SUMMARY]
    if not summary:
        raise StoryError("llm_empty", 502)
    return {"summary": summary}
