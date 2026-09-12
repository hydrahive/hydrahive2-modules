"""Regressionstest für den source-basierten Legacy-Backfill auf project_id."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_scope_migration_assigns_only_unambiguous_sources():
    connection = sqlite3.connect(":memory:")
    connection.executescript((ROOT / "migrations/001_tracks.sql").read_text())
    connection.executescript((ROOT / "migrations/002_source.sql").read_text())
    connection.execute(
        "INSERT INTO module_musicplayer_tracks "
        "(title, filename, size_bytes, uploaded_by, source) VALUES (?, ?, ?, ?, ?)",
        ("Known", "known.mp3", 1, "admin", "projects/project-one/generated/known.mp3"),
    )
    connection.execute(
        "INSERT INTO module_musicplayer_tracks "
        "(title, filename, size_bytes, uploaded_by, source) VALUES (?, ?, ?, ?, ?)",
        ("Unknown", "unknown.mp3", 1, "admin", ""),
    )

    connection.executescript((ROOT / "migrations/003_project_scope.sql").read_text())
    rows = connection.execute(
        "SELECT title, project_id FROM module_musicplayer_tracks ORDER BY id"
    ).fetchall()

    assert rows == [("Known", "project-one"), ("Unknown", None)]
