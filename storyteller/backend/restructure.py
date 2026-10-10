"""C2 – Gliederungs-Umbau ausführen bzw. als Vorschlag ablegen (Spec autor-gliederung-c2.md §2).

``execute``: Schritte planen (_restructure_plan) und als EINE Änderung unter der Sperre des Buchs ausführen – neue
Szenen-Dateien anlegen, Gliederung schreiben (eine Versionserhöhung), danach Gelöschtes in den Papierkorb (wie C1) und
Kapitel-Zusammenfassungen speichern. Scheitert das Schreiben der Gliederung, werden neue Szenen-Dateien wieder entfernt.
Vorschlag: ``proposals/restructure.json`` (genau einer je Buch; ersetzen/verwerfen → Verlauf A2). Übernehmen plant neu
auf dem aktuellen Stand – passt es nicht mehr, bleibt der Vorschlag und es gibt die Fehlermeldung des Schritts.
"""
from __future__ import annotations

from typing import Any

from . import _replaced
from ._book import MAX_SCENES, _existing, _now
from ._files import StoryError, inside, new_id, read_json, write_json, write_scene
from ._locks import locked
from ._names import is_fiction
from ._restructure_plan import Plan, describe, plan
from ._trash import place_of, trash_scene
from ._trash_chapter import trash_chapter
from .proposals import origin_of

_KIND = "restructure"


def _path(project_id: str, book_id: str):
    return _existing(project_id, book_id) / "proposals" / "restructure.json"


def _titles(d) -> dict[str, str]:
    out = {}
    for meta in (d / "scenes").glob("*.json"):
        try:
            out[meta.stem] = read_json(meta).get("title", "")
        except (OSError, ValueError):
            continue
    return out


def _plan(project_id: str, book_id: str, steps: Any) -> tuple[dict, Plan]:
    d = _existing(project_id, book_id)
    st = read_json(d / "structure.json")
    return st, plan(st, steps, new_id=new_id, titles=_titles(d), max_scenes=MAX_SCENES)


def _chapter_titles(st: dict) -> list[str]:
    return [c["title"] for p in st["parts"] for c in p["chapters"]]


def _write_structure(d, st: dict) -> None:
    write_json(d / "structure.json", st)


def _check_busy(project_id: str, book_id: str) -> None:
    from . import runs, team_jobs
    if runs.active_run(project_id, book_id):
        raise StoryError("run_active", 409)
    if any(j["status"] in team_jobs.ACTIVE for j in team_jobs.list_jobs(project_id, book_id)):
        raise StoryError("job_active", 409)


@locked
def execute(project_id: str, book_id: str, steps: Any) -> dict:
    _check_busy(project_id, book_id)
    d = _existing(project_id, book_id)
    old, p = _plan(project_id, book_id, steps)
    created = []
    try:
        for s in p.new_scenes:
            write_scene(d, s["id"], {"id": s["id"], "title": s["title"], "summary": s["summary"], "pov": "",
                                     "status": "idea", "origin": "human", "version": 1, "updated_at": _now()}, "")
            created.append(s["id"])
        p.structure["version"] = old["version"] + 1
        _write_structure(d, p.structure)
    except BaseException:
        for sid in created:
            for ext in ("md", "json"):
                inside(d, "scenes", f"{sid}.{ext}").unlink(missing_ok=True)
        raise
    for sid in p.deleted_scenes:                    # erst nach der Gliederung: Dateien weg = schon nicht mehr im Buch
        trash_scene(project_id, book_id, d, sid, place_of(old, sid))
    for ch in p.deleted_chapters:
        trash_chapter(project_id, book_id, d, ch, ch["place"])
    if p.summaries:
        path = d / "chapters.json"
        data = read_json(path) if path.is_file() else {}
        for cid, text in p.summaries.items():
            prev = data.get(cid) or {"version": 0}
            data[cid] = {"summary": text, "version": prev.get("version", 0) + 1, "updated_at": _now()}
        write_json(path, data)
    book = read_json(d / "book.json")
    write_json(d / "book.json", {**book, "updated_at": _now()})
    from .scenes import get_scene
    return {"structure": p.structure, "ids": p.ids, "lines": describe(p.items, fiction=is_fiction(book["kind"])),
            "scenes": [get_scene(project_id, book_id, s["id"]) for s in p.new_scenes]}


def get(project_id: str, book_id: str) -> dict:
    path = _path(project_id, book_id)
    if not path.is_file():
        raise StoryError("proposal_not_found", 404)
    return read_json(path)


def find(project_id: str, book_id: str) -> dict | None:
    path = _path(project_id, book_id)
    return read_json(path) if path.is_file() else None


def _to_history(project_id: str, book_id: str, *, reason: str, by: str) -> dict | None:
    path = _path(project_id, book_id)
    if not path.is_file():
        return None
    old = read_json(path)
    _replaced.keep(project_id, book_id, _KIND, _KIND, old, reason=reason, by=by)
    path.unlink()
    return old


@locked
def propose(project_id: str, book_id: str, steps: Any, *, author: str, note: str = "", session_id: str = "") -> dict:
    """Prüfen (Trockenlauf) und ablegen. Das Buch bleibt unverändert."""
    st, p = _plan(project_id, book_id, steps)
    book = read_json(_existing(project_id, book_id) / "book.json")
    proposal = {"steps": steps, "lines": describe(p.items, fiction=is_fiction(book["kind"])),
                "before": _chapter_titles(st), "after": _chapter_titles(p.structure),
                "base_structure_version": st["version"], "source": "agent", "author": author[:200],
                "note": note[:500], "session_id": session_id, "at": _now()}
    old = _to_history(project_id, book_id, reason="replaced", by=origin_of(proposal))
    path = _path(project_id, book_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, proposal)
    return {**proposal, "replaced_from": {"author": origin_of(old), "at": old["at"]} if old else None}


@locked
def accept(project_id: str, book_id: str) -> dict:
    proposal = get(project_id, book_id)
    out = execute(project_id, book_id, proposal["steps"])   # Fehler → Vorschlag bleibt
    _path(project_id, book_id).unlink(missing_ok=True)
    return out


@locked
def discard(project_id: str, book_id: str) -> None:
    _to_history(project_id, book_id, reason="discarded", by="")


@locked
def restore(project_id: str, book_id: str, entry_id: str) -> dict:
    entry = _replaced.take(project_id, book_id, _KIND, _KIND, entry_id)
    _to_history(project_id, book_id, reason="restored_over", by="")
    write_json(_path(project_id, book_id), entry["proposal"])
    return entry["proposal"]
