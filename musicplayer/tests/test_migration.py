"""Regressionstests für den deterministischen Legacy-Backfill auf project_id."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _insert(connection: sqlite3.Connection, title: str, uploader: str, source: str) -> None:
    connection.execute(
        "INSERT INTO module_musicplayer_tracks "
        "(title, filename, size_bytes, uploaded_by, source) VALUES (?, ?, ?, ?, ?)",
        (title, f"{title}.mp3", 1, uploader, source),
    )


def test_project_scope_migration_assigns_only_deterministic_sources():
    connection = sqlite3.connect(":memory:")
    connection.executescript((ROOT / "migrations/001_tracks.sql").read_text())
    connection.executescript((ROOT / "migrations/002_source.sql").read_text())

    _insert(connection, "Known", "till", "projects/project-one/generated/known.mp3")
    _insert(connection, "Master", "till", "master/master-agent/generated/old.mp3")
    _insert(connection, "Upload", "till", "")

    # Für `other` existieren zwei mögliche Projekte: der Master-Track muss NULL bleiben.
    _insert(connection, "OtherA", "other", "projects/project-a/generated/a.mp3")
    _insert(connection, "OtherB", "other", "projects/project-b/generated/b.mp3")
    _insert(connection, "Ambiguous", "other", "master/master-agent/generated/ambiguous.mp3")

    connection.executescript((ROOT / "migrations/003_project_scope.sql").read_text())
    rows = connection.execute(
        "SELECT title, project_id FROM module_musicplayer_tracks ORDER BY id"
    ).fetchall()

    assert rows == [
        ("Known", "project-one"),
        ("Master", "project-one"),
        ("Upload", None),
        ("OtherA", "project-a"),
        ("OtherB", "project-b"),
        ("Ambiguous", None),
    ]


def test_media_kind_migration_haelt_bestand_als_audio_mp3():
    connection = sqlite3.connect(":memory:")
    for migration in ("001_tracks.sql", "002_source.sql", "003_project_scope.sql"):
        connection.executescript((ROOT / "migrations" / migration).read_text())
    _insert(connection, "Legacy", "till", "projects/project-one/generated/legacy.mp3")

    connection.executescript((ROOT / "migrations/004_media_kind.sql").read_text())
    row = connection.execute(
        "SELECT media_kind, ext, meta FROM module_musicplayer_tracks WHERE title = 'Legacy'"
    ).fetchone()
    assert row == ("audio", "mp3", "")
