"""Track-Metadaten-Store — eine Zeile je hochgeladenem MP3.

Die DB ist die Wahrheit für die Track-Liste; storage.py hält das Audio-Backing.
Upload/Delete in routes.py halten beide konsistent.
"""
from __future__ import annotations

from hydrahive.db.connection import db

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def add(title: str, filename: str, size_bytes: int, uploaded_by: str, source: str = "") -> int:
    with db() as c:
        cur = c.execute(
            "INSERT INTO module_musicplayer_tracks "
            "(title, filename, size_bytes, uploaded_by, source, created_at) "
            f"VALUES (?, ?, ?, ?, ?, {_NOW})",
            (title, filename, size_bytes, uploaded_by, source),
        )
        return int(cur.lastrowid)


def imported_sources() -> set[str]:
    """Alle bereits importierten Quell-Pfade (für Dedup beim Import)."""
    with db() as c:
        rows = c.execute(
            "SELECT source FROM module_musicplayer_tracks WHERE source <> ''"
        ).fetchall()
    return {r["source"] for r in rows}


def list_all() -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT id, title, size_bytes, uploaded_by, created_at "
            "FROM module_musicplayer_tracks ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [
        {
            "id": int(r["id"]),
            "title": r["title"],
            "size_bytes": int(r["size_bytes"]),
            "uploaded_by": r["uploaded_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def get(track_id: int) -> dict | None:
    with db() as c:
        r = c.execute(
            "SELECT id, title, filename, size_bytes, uploaded_by, created_at "
            "FROM module_musicplayer_tracks WHERE id = ?",
            (track_id,),
        ).fetchone()
    if r is None:
        return None
    return {
        "id": int(r["id"]),
        "title": r["title"],
        "filename": r["filename"],
        "size_bytes": int(r["size_bytes"]),
        "uploaded_by": r["uploaded_by"],
        "created_at": r["created_at"],
    }


def delete(track_id: int) -> str | None:
    """Löscht die Zeile, gibt den Dateinamen zurück (für storage.delete_file)."""
    with db() as c:
        r = c.execute(
            "SELECT filename FROM module_musicplayer_tracks WHERE id = ?",
            (track_id,),
        ).fetchone()
        if r is None:
            return None
        c.execute("DELETE FROM module_musicplayer_tracks WHERE id = ?", (track_id,))
        return r["filename"]
