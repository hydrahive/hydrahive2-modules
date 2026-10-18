"""Drehbuch-Entwurf aus einem Storyteller-Buch (Spec „Bauplan B2“). Liest nur, ändert nichts am Buch.

Eigene Lese-Hilfe statt Import aus dem Storyteller-Modul (Module importieren nicht übereinander). Format laut
storyteller/backend/_book.py: books/<id>/book.json, structure.json (Teile → Kapitel → Szenen-IDs, Steckbriefe),
scenes/<id>.json (title, summary, pov). Kaputte oder fehlende Dateien werden übersprungen.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import _draft, plan
from ._clean import text
from ._store import is_id, project_root, read_json

KIND = {"character": "character", "place": "place", "item": "object"}
_ENDING = r"(?:s|es|'s|’s)?"                # „des Leuchtturms“, „Miras“, „Mira's“ – mehr nicht, sonst wäre „Miranda“ eine Mira
SCENE_WORD = {"en": "Scene"}                  # Titel für Szenen ohne Titel, je Sprache des Buchs; sonst „Szene“


def _books_dir(pid: str) -> Path:
    return project_root(pid) / "storyteller" / "books"


def _dict(path: Path) -> dict:
    data = read_json(path, {}) if path.is_file() and not path.is_symlink() else {}
    return data if isinstance(data, dict) else {}


def _chapters(structure: dict) -> list[dict]:
    out = []
    for part in structure.get("parts") or [] if isinstance(structure.get("parts"), list) else []:
        for ch in (part.get("chapters") or []) if isinstance(part, dict) and isinstance(part.get("chapters"), list) else []:
            if isinstance(ch, dict) and is_id(ch.get("id")):
                scenes = [s for s in ch.get("scenes") or [] if is_id(s)] if isinstance(ch.get("scenes"), list) else []
                out.append({"id": ch["id"], "title": text(ch.get("title"), 200), "scenes": scenes})
    return out


def _entities(structure: dict) -> list[dict]:
    raw = structure.get("entities") if isinstance(structure.get("entities"), list) else []
    return [e for e in raw if isinstance(e, dict) and e.get("kind") in KIND and is_id(e.get("id")) and text(e.get("name"), 200)]


def _book(pid: str, book_id) -> tuple[Path, dict] | None:
    if not is_id(book_id):
        return None
    d = _books_dir(pid) / book_id
    book = _dict(d / "book.json")
    return (d, book) if book and not d.is_symlink() else None


def count(pid: str) -> int:
    d = _books_dir(pid)
    return sum(1 for b in d.iterdir() if _book(pid, b.name)) if d.is_dir() else 0


def list_books(pid: str) -> dict:
    d = _books_dir(pid)
    out = []
    for child in sorted(d.iterdir()) if d.is_dir() else []:
        found = _book(pid, child.name)
        if not found:
            continue
        structure = _dict(found[0] / "structure.json")
        out.append({"id": child.name, "title": text(found[1].get("title"), 200),
                    "chapters": [{"id": c["id"], "title": c["title"], "scenes": len(c["scenes"])} for c in _chapters(structure)],
                    "entities": len(_entities(structure))})
    return {"books": out}


def _element(e: dict) -> dict:
    fields = [f"{text(f.get('key'), 200)}: {text(f.get('value'), 2000)}" for f in e.get("fields") or []
              if isinstance(f, dict) and text(f.get("key"), 200) and text(f.get("value"), 2000)] if isinstance(e.get("fields"), list) else []
    desc = "\n".join(x for x in (text(e.get("description"), 4000), "; ".join(fields)) if x)
    return {"key": e["id"], "kind": KIND[e["kind"]], "name": text(e["name"], 200), "description": desc}


def _names(e: dict) -> list[str]:
    aliases = [a for a in e.get("aliases") or [] if isinstance(a, str) and a.strip()] if isinstance(e.get("aliases"), list) else []
    return [n.strip() for n in [e["name"], *aliases]]


def _mentioned(entities: list[dict], pov: str, words: str) -> list[str]:
    """Steckbriefe der Szene: Perspektive = Name/Alias, oder Name/Alias kommt als Wort in Titel/Zusammenfassung vor."""
    out = []
    for e in entities:
        names = _names(e)
        hit = pov.casefold() in {n.casefold() for n in names} or any(
            re.search(rf"(?<!\w){re.escape(n)}{_ENDING}(?!\w)", words, re.IGNORECASE) for n in names)
        if hit:
            out.append(e["id"])
    return out


def draft(pid: str, data: dict) -> dict:
    found = _book(pid, data.get("book_id"))
    if not found:
        raise plan.PlanError("studio_book_not_found", 404)
    d, book = found
    structure = _dict(d / "structure.json")
    wanted = data.get("chapter_ids")
    chapters = [c for c in _chapters(structure) if not isinstance(wanted, list) or c["id"] in wanted]
    entities = _entities(structure)
    word = SCENE_WORD.get(str(book.get("language") or ""), "Szene")
    ids = [s for c in chapters for s in c["scenes"]]
    scenes = []
    for n, sid in enumerate(ids[:_draft.MAX_SCENES], start=1):
        info = _dict(d / "scenes" / f"{sid}.json")
        title, summary = text(info.get("title"), 200), text(info.get("summary"), 4000)
        scenes.append({"title": title or f"{word} {n}", "description": summary,
                       "element_keys": _mentioned(entities, text(info.get("pov"), 200), f"{title}\n{summary}"), "shots": []})
    if not scenes:
        raise plan.PlanError("studio_book_empty")
    out = _draft.clean({"head": {"title": book.get("title")}, "elements": [_element(e) for e in entities], "scenes": scenes},
                       strict=False)
    return {"draft": out, "truncated": max(0, len(ids) - _draft.MAX_SCENES)}
