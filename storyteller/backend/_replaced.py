"""A2 – Verlauf ersetzter und verworfener Vorschläge (Spec nichts-geht-verloren.md §2).

    proposals/_replaced/<art>/<schlüssel>/<zeit>.json
        {"proposal": {…Meta des alten Vorschlags…}, "text": "…" (nur Art text),
         "reason": "replaced"|"discarded"|"restored_over", "replaced_by": "<Herkunft des neuen>", "replaced_at": "…"}

Arten und Schlüssel: ``text``/``info`` je Szene (Szenen-ID), ``outline`` (Schlüssel „outline“), ``entity`` je Steckbrief
(Steckbrief-ID, neue Steckbriefe unter „new“). Je Schlüssel höchstens ``KEEP`` Einträge (älteste fallen weg).
Nur Ablage: Ersetzen/Zurückholen machen die Vorschlags-Module (unter der Sperre des Buchs).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from ._book import _existing, _now
from ._files import StoryError, check_id, inside, read_json, write_json

KEEP = 10
KINDS = ("text", "info", "outline", "entity")
REASONS = ("replaced", "discarded", "restored_over")   # restored_over: ein älterer wurde zurückgeholt
_ENTRY_RE = re.compile(r"^\d{8}T\d{12}$")
_FMT = "%Y%m%dT%H%M%S%f"


def _key(kind: str, key: str) -> str:
    if kind not in KINDS:
        raise StoryError("kind_invalid")
    if kind == "outline":
        if key != "outline":
            raise StoryError("proposal_not_found", 404)
        return key
    if kind == "entity" and key == "new":
        return key
    return check_id(key, "scene" if kind in ("text", "info") else "entity")


def _dir(project_id: str, book_id: str, kind: str, key: str):
    return inside(_existing(project_id, book_id), "proposals", "_replaced", kind, _key(kind, key))


def scene_dirs(book_dir, scene_id: str):
    """Verlaufs-Ordner einer Szene (Text + Infos) – für Papierkorb und Wiederherstellen."""
    return {k: inside(book_dir, "proposals", "_replaced", k, check_id(scene_id, "scene")) for k in ("text", "info")}


def keep(project_id: str, book_id: str, kind: str, key: str, proposal: dict, *, text: str | None = None,
         reason: str = "replaced", by: str = "") -> dict:
    """Alten Vorschlag in den Verlauf legen. Aufrufer hält die Sperre des Buchs."""
    if reason not in REASONS:
        raise StoryError("reason_invalid")
    d = _dir(project_id, book_id, kind, key)
    d.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    while (d / f"{now.strftime(_FMT)}.json").exists():   # zwei Einträge in derselben Mikrosekunde
        now += timedelta(microseconds=1)
    entry = {"proposal": proposal, "reason": reason, "replaced_by": by[:200], "replaced_at": _now()}
    if text is not None:
        entry["text"] = text
    write_json(d / f"{now.strftime(_FMT)}.json", entry)
    for old in sorted(d.glob("*.json"), reverse=True)[KEEP:]:
        old.unlink(missing_ok=True)
    return entry


def _summary(kind: str, entry_id: str, e: dict) -> dict:
    p = e["proposal"]
    out = {"id": entry_id, "kind": kind, "at": p.get("at", ""), "source": p.get("source", "run"),
           "author": p.get("author", ""), "note": p.get("note", ""), "model": p.get("model", ""),
           "reason": e["reason"], "replaced_by": e.get("replaced_by", ""), "replaced_at": e.get("replaced_at", "")}
    if kind == "text":
        out["words"] = p.get("words", 0)
    elif kind == "info":
        out["fields"] = p.get("fields", {})
    elif kind == "outline":
        out["chapters"] = len((p.get("outline") or {}).get("chapters", []))
    else:
        out.update(entity_id=p.get("entity_id", ""), name=(p.get("changes") or {}).get("name", ""))
    return out


def history(project_id: str, book_id: str, kind: str, key: str) -> list[dict]:
    d = _dir(project_id, book_id, kind, key)
    files = sorted(d.glob("*.json"), reverse=True) if d.is_dir() else []
    return [_summary(kind, p.stem, read_json(p)) for p in files]


def _entry_path(project_id: str, book_id: str, kind: str, key: str, entry_id: str):
    if not isinstance(entry_id, str) or not _ENTRY_RE.match(entry_id):
        raise StoryError("proposal_not_found", 404)
    path = inside(_dir(project_id, book_id, kind, key), f"{entry_id}.json")
    if not path.is_file():
        raise StoryError("proposal_not_found", 404)
    return path


def get(project_id: str, book_id: str, kind: str, key: str, entry_id: str) -> dict:
    """Eintrag mit Text (Art text) bzw. ganzem Vorschlag."""
    e = read_json(_entry_path(project_id, book_id, kind, key, entry_id))
    return {**_summary(kind, entry_id, e), "proposal": e["proposal"], **({"text": e["text"]} if "text" in e else {})}


def take(project_id: str, book_id: str, kind: str, key: str, entry_id: str) -> dict:
    """Eintrag entnehmen (zum Zurückholen). Aufrufer hält die Sperre."""
    path = _entry_path(project_id, book_id, kind, key, entry_id)
    e = read_json(path)
    path.unlink()
    return e
