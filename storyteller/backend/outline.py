"""Ghostwriter G2 – Gliederung aus Idee (Spec ghostwriter.md §9.1).

``generate`` fragt die KI nach einer Gliederung als JSON (Kapitel → Szenen mit Zusammenfassung,
Steckbriefe) und prüft sie; gespeichert wird nichts. ``apply`` übernimmt eine (in der Oberfläche
bearbeitete) Gliederung: hängt die Kapitel an den letzten Teil an bzw. ersetzt die einzige leere Szene
eines neuen Buchs. Steckbriefe werden nur für neue Namen ergänzt. Versionsprüfung der Struktur.
"""
from __future__ import annotations

import json
import re
from typing import Any

from hydrahive.llm.client import complete

from . import storage
from ._book import MAX_SCENES, _existing, _now
from ._files import StoryError, new_id, read_json, write_json, write_scene
from ._ghost_settings import ghost_of
from ._locks import locked
from ._names import KIND_LABEL, LANGUAGE_LABEL, is_fiction
from ._think import strip_think
from ._trash import trash_scene
from .storage import Conflict

MAX_CHAPTERS, MAX_SCENES_PER_CHAPTER = 40, 8
_KINDS = ("character", "place", "item")
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _text(v: Any, limit: int, *, required: bool) -> str:
    if not isinstance(v, str) or len(v) > limit or (required and not v.strip()):
        raise StoryError("outline_invalid")
    return v.strip()


def validate(data: Any) -> dict:
    """Form und Grenzen prüfen, Text säubern. Steckbriefe mit unbekannter Art werden Figuren."""
    if not isinstance(data, dict) or not isinstance(data.get("chapters"), list):
        raise StoryError("outline_invalid")
    chapters = data["chapters"]
    if not 1 <= len(chapters) <= MAX_CHAPTERS:
        raise StoryError("outline_invalid")
    out = []
    for c in chapters:
        if not isinstance(c, dict) or not isinstance(c.get("scenes"), list) or not 1 <= len(c["scenes"]) <= MAX_SCENES_PER_CHAPTER:
            raise StoryError("outline_invalid")
        scenes = []
        for s in c["scenes"]:
            if not isinstance(s, dict):
                raise StoryError("outline_invalid")
            scenes.append({"title": _text(s.get("title"), 200, required=True),
                           "summary": _text(s.get("summary"), 2000, required=True),
                           "pov": _text(s.get("pov") or "", 200, required=False)})
        out.append({"title": _text(c.get("title"), 200, required=True), "scenes": scenes})
    entities = []
    for e in data.get("entities") or []:
        if isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip() and len(e["name"]) <= 200:
            desc = e.get("description")
            entities.append({"name": e["name"].strip(), "kind": e.get("kind") if e.get("kind") in _KINDS else "character",
                             "description": desc[:2000] if isinstance(desc, str) else ""})
    return {"chapters": out, "entities": entities[:100]}


def _parse(raw: str) -> Any:
    m = _JSON_RE.search(strip_think(raw or ""))
    if not m:
        raise ValueError("kein JSON")
    return json.loads(m.group(0))


async def generate(project_id: str, book_id: str, *, idea: str, chapters: int, scenes_per_chapter: int,
                   hints: str = "", model: str | None = None) -> dict:
    book = storage.get_book(project_id, book_id)
    if not 1 <= chapters <= MAX_CHAPTERS or not 1 <= scenes_per_chapter <= MAX_SCENES_PER_CHAPTER:
        raise StoryError("outline_size_invalid")
    lang = LANGUAGE_LABEL.get(book["language"], book["language"])
    unit = "Szenen" if is_fiction(book["kind"]) else "Abschnitte"
    system = (f"Du planst ein Buch ({KIND_LABEL.get(book['kind'], book['kind'])}) auf {lang}. Antworte NUR mit JSON, "
              'ohne Erklärung: {"chapters": [{"title": "...", "scenes": [{"title": "...", "summary": "2–4 Sätze, was '
              'passiert", "pov": "Perspektive oder leer"}]}], "entities": [{"name": "...", "kind": "character|place|item", '
              '"description": "1–2 Sätze"}]}. Die Zusammenfassungen bauen aufeinander auf und erzählen die ganze Handlung.')
    prompt = (f"TITEL: {book['title']}\nZIELGRUPPE: {book.get('audience') or 'nicht angegeben'}\n"
              f"IDEE: {idea.strip() or book.get('idea') or '–'}\n"
              + (f"STIL: {ghost_of(book)['style']}\n" if ghost_of(book)["style"].strip() else "")
              + (f"HINWEISE: {hints.strip()}\n" if hints.strip() else "")
              + f"\nUMFANG: {chapters} Kapitel mit je {scenes_per_chapter} {unit}.")
    use_model = model or ghost_of(book)["model"] or book.get("model") or None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    max_tokens = min(16000, 400 + chapters * scenes_per_chapter * 220)
    raw = await complete(messages, model=use_model, temperature=0.7, max_tokens=max_tokens)
    for attempt in range(2):
        try:
            return validate(_parse(raw))
        except (ValueError, StoryError):
            if attempt:
                raise StoryError("outline_invalid", 502) from None
            messages += [{"role": "assistant", "content": raw or ""},
                         {"role": "user", "content": "Das war kein gültiges JSON in der verlangten Form. Bitte nur das JSON."}]
            raw = await complete(messages, model=use_model, temperature=0.3, max_tokens=max_tokens)
    raise StoryError("outline_invalid", 502)   # nicht erreichbar


@locked
def apply(project_id: str, book_id: str, outline_data: dict, base_version: int) -> dict:
    data = validate(outline_data)
    d = _existing(project_id, book_id)
    st = read_json(d / "structure.json")
    if st["version"] != base_version:
        raise Conflict(st)
    ids = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
    lone = storage.get_scene(project_id, book_id, ids[0]) if len(ids) == 1 else None
    replace = lone is not None and not lone["text"].strip() and not lone["summary"].strip()
    new_count = sum(len(c["scenes"]) for c in data["chapters"])
    if len(ids) - (1 if replace else 0) + new_count > MAX_SCENES:
        raise StoryError("too_many_scenes")
    part = st["parts"][-1]
    if replace:
        st["parts"][0]["chapters"] = []
        part = st["parts"][0]
    created = []
    for c in data["chapters"]:
        sids = []
        for s in c["scenes"]:
            sid = new_id()
            write_scene(d, sid, {"id": sid, "title": s["title"], "summary": s["summary"], "pov": s["pov"],
                                 "status": "idea", "origin": "human", "version": 1, "updated_at": _now()}, "")
            sids.append(sid)
        created += sids
        part["chapters"].append({"id": new_id(), "title": c["title"], "scenes": sids})
    known = {e["name"].lower() for e in st.get("entities", [])}
    for e in data["entities"]:
        if e["name"].lower() not in known:
            st.setdefault("entities", []).append({"id": new_id(), "kind": e["kind"], "name": e["name"], "aliases": [],
                                                  "description": e["description"], "fields": []})
            known.add(e["name"].lower())
    st["version"] += 1
    write_json(d / "structure.json", st)
    if replace:
        trash_scene(project_id, book_id, d, ids[0])   # leere Platzhalter-Szene: Papierkorb wie jede gelöschte
    return {"structure": st, "scenes": {s: storage.get_scene(project_id, book_id, s) for s in created}}
