"""Bestehendes Buch in ein eigenes Buch-Projekt mit Schreib-Team umziehen (T1f, Plan schreib-team-t1f-umzug.md).

Kopieren → prüfen → Quelle sichern, nie direkt verschieben: Bis zum letzten Schritt bleibt das Buch im alten Projekt
unverändert; scheitert etwas, wird das neue Projekt wieder entfernt (Autor + Helfer gehen mit). Erst wenn die Kopie
Szene für Szene gleich ist, wandert die Quelle in den Papierkorb des alten Projekts (``trash/moved/<id>-<zeit>``) –
das ist der Rückweg. ``jobs/`` (Team-Aufträge des alten Projekts) bleibt zurück. Die Rechte prüft die Route.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import runs, storage, team_jobs
from .._book import _now, book_dir
from .._files import StoryError, read_json, story_root, write_json
from .._locks import book_lock
from . import setup

logger = logging.getLogger(__name__)
_SKIP = ("jobs",)


def is_book_project(project_id: str) -> bool:
    from hydrahive.projects import config as project_config
    meta = ((project_config.get(project_id) or {}).get("metadata") or {}).get("storyteller")
    return isinstance(meta, dict)


def _fingerprint(d: Path) -> tuple[int, str]:
    """(Anzahl Szenen, Prüfsumme über Gliederung und alle Szenentexte) – Kopie muss gleich sein."""
    h = hashlib.sha256()
    for p in [d / "structure.json", *sorted((d / "scenes").glob("*"))]:
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return len(list((d / "scenes").glob("*.md"))), h.hexdigest()


def _copy_book(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*_SKIP))


def _check(project_id: str, book_id: str) -> dict:
    if is_book_project(project_id):
        raise StoryError("already_book_project", 409)
    book = storage.get_book(project_id, book_id)
    if runs.active_run(project_id, book_id):
        raise StoryError("run_active", 409)
    if any(j["status"] in team_jobs.ACTIVE for j in team_jobs.list_jobs(project_id, book_id)):
        raise StoryError("job_active", 409)
    if not book.get("model") and not setup.default_model():
        raise StoryError("no_model", 409)
    setup.check_model(book.get("model") or setup.default_model())   # sonst HTTP 500 mitten im Anlegen
    return book


def move_book(username: str, project_id: str, book_id: str) -> dict[str, Any]:
    with book_lock(project_id, book_id):
        book = _check(project_id, book_id)
        title = book["title"].strip()
        team = setup.new_team_project(username, title, book.get("model") or setup.default_model())
        new_pid = team["project_id"]
        src = book_dir(project_id, book_id)
        try:
            dst = book_dir(new_pid, book_id)
            dst.parent.mkdir(parents=True, exist_ok=True)
            _copy_book(src, dst)
            if _fingerprint(dst) != _fingerprint(src):
                raise StoryError("move_check_failed", 500)
            old_trash = story_root(project_id) / "trash" / book_id
            if old_trash.is_dir():
                shutil.copytree(old_trash, story_root(new_pid) / "trash" / book_id)
            write_json(dst / "book.json", {**read_json(dst / "book.json"),
                                           "moved_from": {"project_id": project_id, "at": _now()}})
            setup.mark_book_project(new_pid, book_id)
        except Exception:
            logger.exception("storyteller: Umzug von Buch %s aus %s fehlgeschlagen – räume auf", book_id, project_id)
            setup.drop_project(new_pid)
            raise
        # Ab hier ist die Kopie vollständig und geprüft: Quelle sichern (Rückweg), Papierkorb-Teil ist mitgenommen.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        backup = story_root(project_id) / "trash" / "moved" / f"{book_id}-{stamp}"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(backup))
        if old_trash.is_dir():
            shutil.move(str(old_trash), str(backup / "_trash"))
    logger.info("storyteller: Buch %s aus %s in eigenes Projekt %s umgezogen", book_id, project_id, new_pid)
    return {"project_id": new_pid, "book_id": book_id,
            "backup": str(backup.relative_to(story_root(project_id)))}
