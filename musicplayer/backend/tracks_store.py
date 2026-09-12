"""DB-Zugriff für projektgebundene Musicplayer-Tracks."""
from __future__ import annotations

from hydrahive.db.connection import db

_COLUMNS = "id, project_id, title, filename, size_bytes, uploaded_by, created_at, source"


def list_all(project_id: str) -> list[dict]:
    with db() as connection:
        rows = connection.execute(
            f"SELECT {_COLUMNS} FROM module_musicplayer_tracks "
            "WHERE project_id = ? ORDER BY created_at DESC, id DESC",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get(project_id: str, track_id: int) -> dict | None:
    with db() as connection:
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM module_musicplayer_tracks "
            "WHERE project_id = ? AND id = ?",
            (project_id, track_id),
        ).fetchone()
        return dict(row) if row else None


def add(
    project_id: str,
    *,
    title: str,
    filename: str,
    size_bytes: int,
    uploaded_by: str,
    source: str = "",
) -> dict:
    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO module_musicplayer_tracks "
            "(project_id, title, filename, size_bytes, uploaded_by, source) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, title, filename, size_bytes, uploaded_by, source),
        )
        row = connection.execute(
            f"SELECT {_COLUMNS} FROM module_musicplayer_tracks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def delete(project_id: str, track_id: int) -> bool:
    with db() as connection:
        cursor = connection.execute(
            "DELETE FROM module_musicplayer_tracks WHERE project_id = ? AND id = ?",
            (project_id, track_id),
        )
        return cursor.rowcount > 0


def imported_sources(project_id: str) -> set[str]:
    with db() as connection:
        rows = connection.execute(
            "SELECT source FROM module_musicplayer_tracks "
            "WHERE project_id = ? AND source IS NOT NULL AND source != ''",
            (project_id,),
        ).fetchall()
        return {str(row["source"]) for row in rows}


def source_exists(project_id: str, source: str) -> bool:
    with db() as connection:
        row = connection.execute(
            "SELECT 1 FROM module_musicplayer_tracks WHERE project_id = ? AND source = ? LIMIT 1",
            (project_id, source),
        ).fetchone()
        return row is not None
