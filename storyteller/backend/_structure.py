"""Prüfung einer vom Client gesendeten Struktur (Teile → Kapitel → Szenen-IDs, Steckbriefe)."""
from __future__ import annotations

from typing import Any

from ._files import StoryError, check_id

MAX_ENTITIES = 500
_ENTITY_KINDS = ("character", "place", "item")


def _title(v: Any) -> str:
    if not isinstance(v, str) or not v.strip() or len(v) > 200:
        raise StoryError("title_invalid")
    return v.strip()


def _entity(e: Any) -> dict:
    if not isinstance(e, dict) or e.get("kind") not in _ENTITY_KINDS:
        raise StoryError("entity_invalid")
    aliases = e.get("aliases", [])
    fields = e.get("fields", [])
    if not isinstance(aliases, list) or len(aliases) > 50 or not all(isinstance(a, str) and len(a) <= 200 for a in aliases):
        raise StoryError("entity_invalid")
    if not isinstance(fields, list) or len(fields) > 100:
        raise StoryError("entity_invalid")
    clean_fields = []
    for f in fields:
        if not isinstance(f, dict) or not all(isinstance(f.get(k, ""), str) and len(f.get(k, "")) <= 2000 for k in ("key", "value")):
            raise StoryError("entity_invalid")
        clean_fields.append({"key": f.get("key", ""), "value": f.get("value", "")})
    desc = e.get("description", "")
    if not isinstance(desc, str) or len(desc) > 10_000:
        raise StoryError("entity_invalid")
    return {"id": check_id(e.get("id", ""), "entity"), "kind": e["kind"], "name": _title(e.get("name")),
            "aliases": aliases, "description": desc, "fields": clean_fields}


def validate_structure(structure: Any, existing_scenes: set[str]) -> dict:
    """Gibt eine bereinigte Struktur zurück. Jede vorhandene Szene muss genau einmal vorkommen."""
    if not isinstance(structure, dict) or not isinstance(structure.get("parts"), list) or not structure["parts"]:
        raise StoryError("structure_invalid")
    seen: list[str] = []
    parts = []
    for p in structure["parts"]:
        if not isinstance(p, dict) or not isinstance(p.get("chapters"), list) or not p["chapters"]:
            raise StoryError("structure_invalid")
        chapters = []
        for c in p["chapters"]:
            if not isinstance(c, dict) or not isinstance(c.get("scenes"), list) or not c["scenes"]:
                raise StoryError("structure_invalid")
            ids = [check_id(s, "scene") for s in c["scenes"]]
            seen.extend(ids)
            chapters.append({"id": check_id(c.get("id", ""), "chapter"), "title": _title(c.get("title")), "scenes": ids})
        parts.append({"id": check_id(p.get("id", ""), "part"), "title": _title(p.get("title")), "chapters": chapters})
    if len(seen) != len(set(seen)) or set(seen) != existing_scenes:
        raise StoryError("structure_scenes_mismatch")
    entities = structure.get("entities", [])
    if not isinstance(entities, list) or len(entities) > MAX_ENTITIES:
        raise StoryError("entity_invalid")
    clean_entities = [_entity(e) for e in entities]
    if len({e["id"] for e in clean_entities}) != len(clean_entities):
        raise StoryError("entity_invalid")
    return {"parts": parts, "entities": clean_entities}
