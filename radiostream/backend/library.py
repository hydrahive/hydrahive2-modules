"""Bibliothek in der Modul-DB: Titel schreiben, Stand je Pfad, Fehlerliste. Suche steht in search.py."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from hydrahive.db.connection import db

FIELDS = ("artist", "album_artist", "title", "album", "genre", "year", "track_no", "duration_s", "bitrate",
          "sample_rate", "format", "replaygain_db")
MAX_ERRORS = 5000


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def track_id(source_id: str, rel_path: str) -> str:
    return "t_" + hashlib.sha256(f"{source_id}\x00{rel_path}".encode()).hexdigest()[:24]


def known(source_id: str) -> dict[str, tuple[int, int, str]]:
    """rel_path → (size, mtime, state) aller bekannten Titel der Quelle."""
    with db() as conn:
        rows = conn.execute("SELECT rel_path, size, mtime, state FROM module_radiostream_tracks WHERE source_id = ?",
                            (source_id,)).fetchall()
    return {r[0]: (r[1], r[2], r[3]) for r in rows}


def upsert_batch(source_id: str, items: list[tuple[str, int, int, dict]]) -> None:
    """(rel_path, size, mtime, tags) in einem Rutsch speichern – ein Paket = eine Transaktion (Fortsetzen)."""
    now = _now()
    cols = ", ".join(FIELDS)
    marks = ", ".join("?" for _ in FIELDS)
    upd = ", ".join(f"{f} = excluded.{f}" for f in FIELDS)
    with db() as conn:
        for rel, size, mtime, tags in items:
            conn.execute(
                f"INSERT INTO module_radiostream_tracks (track_id, source_id, rel_path, size, mtime, {cols}, state, "  # noqa: S608
                f"error_code, first_seen, last_seen) VALUES (?, ?, ?, ?, ?, {marks}, 'ok', NULL, ?, ?) "
                f"ON CONFLICT(source_id, rel_path) DO UPDATE SET size = excluded.size, mtime = excluded.mtime, {upd}, "
                "state = 'ok', error_code = NULL, last_seen = excluded.last_seen",
                (track_id(source_id, rel), source_id, rel, size, mtime, *(tags.get(f) for f in FIELDS), now, now))
        for rel, *_ in items:   # jetzt lesbar → alter Eintrag in der Fehlerliste weg
            conn.execute("DELETE FROM module_radiostream_scan_errors WHERE source_id = ? AND rel_path = ?",
                         (source_id, rel))
        conn.commit()


def set_state(source_id: str, rel_paths: list[str], state: str) -> int:
    if not rel_paths:
        return 0
    n = 0
    with db() as conn:
        for i in range(0, len(rel_paths), 500):
            chunk = rel_paths[i:i + 500]
            cur = conn.execute(
                "UPDATE module_radiostream_tracks SET state = ?, last_seen = ? WHERE source_id = ? AND rel_path IN "
                "(%s) AND state != ?" % ",".join("?" for _ in chunk), (state, _now(), source_id, *chunk, state))  # noqa: S608
            n += cur.rowcount
        conn.commit()
    return n


def add_errors(source_id: str, errors: list[tuple[str, str]]) -> None:
    if not errors:
        return
    now = _now()
    with db() as conn:
        for rel, code in errors:
            conn.execute("DELETE FROM module_radiostream_scan_errors WHERE source_id = ? AND rel_path = ?",
                         (source_id, rel))
            conn.execute("INSERT INTO module_radiostream_scan_errors (source_id, rel_path, code, at) "
                         "VALUES (?, ?, ?, ?)", (source_id, rel, code, now))
        conn.execute("DELETE FROM module_radiostream_scan_errors WHERE id NOT IN (SELECT id FROM "
                     "module_radiostream_scan_errors ORDER BY id DESC LIMIT ?)", (MAX_ERRORS,))
        conn.commit()


def scan_errors() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT rel_path, code, at FROM module_radiostream_scan_errors ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def by_path(rel_path: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM module_radiostream_tracks WHERE rel_path = ?", (rel_path,)).fetchone()
    return dict(row) if row else None


def by_id(tid: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM module_radiostream_tracks WHERE track_id = ?", (tid,)).fetchone()
    return dict(row) if row else None


def count() -> int:
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM module_radiostream_tracks WHERE state = 'ok'").fetchone()[0]


def all_tracks() -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM module_radiostream_tracks").fetchall()]
