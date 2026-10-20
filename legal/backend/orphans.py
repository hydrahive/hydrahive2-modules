"""Verwaiste Fälle aufräumen (Plan L2 Schritt 6, Spec §4.2). Einen Kern-Hook für Projekt-Löschungen gibt es nicht.

Ablauf je Lauf: Fall ohne Projekt → ``orphaned_at`` setzen (ab da für Routen/Werkzeuge unsichtbar). Taucht das Projekt
wieder auf → Markierung aufheben. Verwaist seit mehr als 30 Tagen → komplette Fallakte als JSON (Rechte 0600) nach
``data_dir/legal/archive/`` sichern und erst danach die Zeilen löschen. Scheitert die Sicherung, wird nichts gelöscht.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

GRACE = timedelta(days=30)
_CHILD_TABLES = ("module_legal_parties", "module_legal_deadlines", "module_legal_notes", "module_legal_proposals",
                 "module_legal_correspondence")
_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _project_exists(project_id: str) -> bool:
    from hydrahive.projects._config_io import get as get_project
    return get_project(project_id) is not None


def _archive_dir() -> Path:
    from hydrahive.settings import settings
    return settings.data_dir / "legal" / "archive"


def _dump(project_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {"format": "hydrahive.legal.case v1", "project_id": project_id}
    with db() as c:
        for key, table in (("case", "module_legal_cases"), ("parties", _CHILD_TABLES[0]),
                           ("deadlines", _CHILD_TABLES[1]), ("notes", _CHILD_TABLES[2]),
                           ("proposals", _CHILD_TABLES[3]), ("correspondence", _CHILD_TABLES[4])):
            cur = c.execute(f"SELECT * FROM {table} WHERE project_id = ? ORDER BY rowid", (project_id,))
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
            out[key] = rows[0] if key == "case" else rows
    return out


def _write_archive(project_id: str, data: dict[str, Any], now: datetime) -> Path:
    target = _archive_dir()
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = target / f"{now.strftime('%Y%m%dT%H%M%SZ')}-{project_id}.json"
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


def sweep(*, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    with db() as c:
        rows = c.execute("SELECT project_id, orphaned_at FROM module_legal_cases").fetchall()
    marked = archived = 0
    for pid, orphaned_at in rows:
        exists = _project_exists(pid)
        if exists:
            if orphaned_at is not None:
                with db() as c:
                    c.execute("UPDATE module_legal_cases SET orphaned_at = NULL WHERE project_id = ?", (pid,))
                logger.info("Recht: Fall %s hat wieder ein Projekt – Markierung aufgehoben", pid)
            continue
        if orphaned_at is None:
            with db() as c:
                c.execute("UPDATE module_legal_cases SET orphaned_at = ? WHERE project_id = ?",
                          (now.strftime(_FMT), pid))
            marked += 1
            continue
        since = datetime.strptime(orphaned_at, _FMT).replace(tzinfo=UTC)
        if now - since <= GRACE:
            continue
        path = _write_archive(pid, _dump(pid), now)
        with db() as c:
            for table in (*_CHILD_TABLES, "module_legal_cases"):
                c.execute(f"DELETE FROM {table} WHERE project_id = ?", (pid,))
        archived += 1
        logger.info("Recht: verwaister Fall %s gesichert (%s) und gelöscht", pid, path.name)
    return {"marked": marked, "archived": archived}


async def job() -> None:
    """Modul-Job (täglich): läuft im Thread, damit die Event-Loop frei bleibt."""
    import asyncio
    await asyncio.to_thread(sweep)
