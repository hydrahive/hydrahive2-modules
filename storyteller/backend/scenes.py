"""Storyteller — Szenen: lesen, speichern (mit Versionsprüfung), anlegen, löschen; Kapitel anlegen."""
from __future__ import annotations

import logging
from typing import Any

from ._files import StoryError, count_words, new_id, read_json, scene_paths, text_sha, write_json, write_scene
from ._ghost_settings import next_origin
from ._locks import locked
from ._trash import place_of, trash_scene
from ._book import MAX_SCENE_BYTES, MAX_SCENES, Conflict, _clip, _existing, _now, book_dir

logger = logging.getLogger(__name__)
_SCENE_FIELDS = {"title": 200, "summary": 2000, "pov": 200}
_STATUSES = ("idea", "draft", "revised", "done")


def get_scene(project_id: str, book_id: str, scene_id: str) -> dict:
    d = _existing(project_id, book_id)
    meta_path, text_path = scene_paths(d, scene_id)
    meta = read_json(meta_path)
    text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
    sha = meta.pop("text_sha", None)
    if sha is not None and sha != text_sha(text):
        # Absturz zwischen Text und Infos: der Text auf der Platte gilt (nichts geht verloren), das nächste
        # Speichern erhöht die Version und schreibt den Hash neu.
        logger.warning("storyteller: Szene %s/%s – Text passt nicht zur gespeicherten Version %s",
                       book_id, scene_id, meta.get("version"))
    return {"origin": "human", **meta, "text": text}


def scene_info(project_id: str, book_id: str, scene_id: str) -> dict:
    """Infos einer Szene ohne Text (Titel, Zusammenfassung, Perspektive, Stand, Version, Wörter) – für das Gedächtnis
    und Listen, die keinen Volltext brauchen (A4)."""
    meta_path, text_path = scene_paths(_existing(project_id, book_id), scene_id)
    meta = read_json(meta_path)
    meta.pop("text_sha", None)
    if "words" not in meta:   # Szene vor 0.17.0: einmal aus dem Text zählen
        meta["words"] = count_words(text_path.read_text(encoding="utf-8")) if text_path.exists() else 0
    return {"origin": "human", **meta}


@locked
def save_scene(project_id: str, book_id: str, scene_id: str, data: dict[str, Any], base_version: int) -> dict:
    current = get_scene(project_id, book_id, scene_id)
    if current["version"] != base_version:
        raise Conflict(current)
    patch = _clip(_SCENE_FIELDS, data)
    if "status" in data:
        if data["status"] not in _STATUSES:
            raise StoryError("status_invalid")
        patch["status"] = data["status"]
    text = data.get("text", current["text"])
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_SCENE_BYTES:
        raise StoryError("text_too_long")
    meta = {k: v for k, v in current.items() if k != "text"}
    meta.update(patch, origin=next_origin(current["origin"], data, text != current["text"]),
                version=current["version"] + 1, updated_at=_now(), words=count_words(text))
    write_scene(_existing(project_id, book_id), scene_id, meta, text)
    _touch(project_id, book_id)
    return {**meta, "text": text}


@locked
def add_scene(project_id: str, book_id: str, chapter_id: str, title: str = "", after: str | None = None) -> dict:
    d = _existing(project_id, book_id)
    st = read_json(d / "structure.json")
    chapters = [c for p in st["parts"] for c in p["chapters"]]
    chapter = next((c for c in chapters if c["id"] == chapter_id), None)
    if chapter is None:
        raise StoryError("chapter_not_found", 404)
    if sum(len(c["scenes"]) for c in chapters) >= MAX_SCENES:
        raise StoryError("too_many_scenes")
    if not isinstance(title, str) or len(title) > 200:
        raise StoryError("title_invalid")
    sid = new_id()
    meta = {"id": sid, "title": title.strip() or "…", "summary": "", "pov": "", "status": "idea",
            "origin": "human", "version": 1, "updated_at": _now()}
    write_scene(d, sid, meta, "")
    at = chapter["scenes"].index(after) + 1 if after in chapter["scenes"] else len(chapter["scenes"])
    chapter["scenes"].insert(at, sid)
    st["version"] += 1
    write_json(d / "structure.json", st)
    return {"scene": {**meta, "text": ""}, "structure": st}


@locked
def add_chapter(project_id: str, book_id: str, part_id: str, title: str, scene_title: str) -> dict:
    """Neues Kapitel am Ende des Teils, mit einer leeren Szene (ein Kapitel ist nie leer)."""
    d = _existing(project_id, book_id)
    st = read_json(d / "structure.json")
    part = next((p for p in st["parts"] if p["id"] == part_id), None)
    if part is None:
        raise StoryError("part_not_found", 404)
    if sum(len(c["scenes"]) for p in st["parts"] for c in p["chapters"]) >= MAX_SCENES:
        raise StoryError("too_many_scenes")
    for t in (title, scene_title):
        if not isinstance(t, str) or not t.strip() or len(t) > 200:
            raise StoryError("title_invalid")
    sid = new_id()
    meta = {"id": sid, "title": scene_title.strip(), "summary": "", "pov": "", "status": "idea",
            "origin": "human", "version": 1, "updated_at": _now()}
    write_scene(d, sid, meta, "")
    part["chapters"].append({"id": new_id(), "title": title.strip(), "scenes": [sid]})
    st["version"] += 1
    write_json(d / "structure.json", st)
    return {"scene": {**meta, "text": ""}, "structure": st}


@locked
def remove_scene(project_id: str, book_id: str, scene_id: str) -> dict:
    d = _existing(project_id, book_id)
    st = read_json(d / "structure.json")
    chapter = next((c for p in st["parts"] for c in p["chapters"] if scene_id in c["scenes"]), None)
    if chapter is None:
        raise StoryError("scene_not_found", 404)
    if len(chapter["scenes"]) <= 1:
        raise StoryError("last_scene")
    place = place_of(st, scene_id)   # A3: alte Stelle merken, damit Wiederherstellen dorthin zurückfindet
    chapter["scenes"].remove(scene_id)
    st["version"] += 1
    write_json(d / "structure.json", st)
    trash_scene(project_id, book_id, d, scene_id, place)   # Papierkorb statt endgültig löschen
    return st


def _touch(project_id: str, book_id: str) -> None:
    """Buch als „zuletzt bearbeitet“ markieren, ohne die Kopf-Version zu erhöhen."""
    d = book_dir(project_id, book_id)
    book = read_json(d / "book.json")
    book["updated_at"] = _now()
    write_json(d / "book.json", book)
