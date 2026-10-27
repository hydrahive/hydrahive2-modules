"""Musikquelle speichern (Etappe 1: genau eine). Nur Adresse + NAME des Safe-Eintrags, nie das Passwort."""
from __future__ import annotations

from datetime import datetime, timezone

from hydrahive.db.connection import db

SOURCE_ID = "main"
_COLS = ("source_id, owner, url, credential_name, state, last_scan_started, last_scan_finished, last_scan_error, "
         "created_at, updated_at")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get() -> dict | None:
    with db() as conn:
        row = conn.execute(f"SELECT {_COLS} FROM module_radiostream_sources WHERE source_id = ?",
                           (SOURCE_ID,)).fetchone()
    return dict(row) if row else None


def save(*, owner: str, url: str, credential_name: str) -> dict:
    now = _now()
    with db() as conn:
        conn.execute(
            "INSERT INTO module_radiostream_sources (source_id, owner, url, credential_name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET owner = excluded.owner, "
            "url = excluded.url, credential_name = excluded.credential_name, state = 'idle', "
            "last_scan_error = NULL, updated_at = excluded.updated_at",
            (SOURCE_ID, owner, url, credential_name, now, now))
        conn.commit()
    return get() or {}


def mark(state: str, *, started: bool = False, finished: bool = False, error: str | None = None) -> None:
    now = _now()
    sets, args = ["state = ?", "last_scan_error = ?", "updated_at = ?"], [state, error, now]
    if started:
        sets.append("last_scan_started = ?")
        args.append(now)
    if finished:
        sets.append("last_scan_finished = ?")
        args.append(now)
    with db() as conn:
        conn.execute(f"UPDATE module_radiostream_sources SET {', '.join(sets)} WHERE source_id = ?",
                     (*args, SOURCE_ID))
        conn.commit()
