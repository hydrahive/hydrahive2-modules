"""Parametrisierte Persistenz für Fälle, Artefakte und Jobs."""
from __future__ import annotations

import uuid
from typing import Any

from hydrahive.db.connection import db

from .models import CaseIn


def _case(row) -> dict[str, Any]:
    value = dict(row)
    value["authorized"] = bool(value["authorized"])
    return value


def create_case(username: str, body: CaseIn) -> dict[str, Any]:
    case_id = str(uuid.uuid4())
    with db() as connection:
        connection.execute(
            "INSERT INTO module_zerlege_cases "
            "(id, project_id, created_by, title, target, question, purpose, authorized, authorization_note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (case_id, body.project_id, username, body.title.strip(), body.target.strip(),
             body.question.strip(), body.purpose, body.authorization_note.strip()),
        )
    return get_case(case_id)  # type: ignore[return-value]


def get_case(case_id: str) -> dict[str, Any] | None:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM module_zerlege_cases WHERE id = ?", (case_id,)
        ).fetchone()
        if not row:
            return None
        artifacts = connection.execute(
            "SELECT * FROM module_zerlege_artifacts WHERE case_id = ? ORDER BY created_at, id",
            (case_id,),
        ).fetchall()
        jobs = connection.execute(
            "SELECT * FROM module_zerlege_jobs WHERE case_id = ? ORDER BY created_at, id",
            (case_id,),
        ).fetchall()
    value = _case(row)
    value["artifacts"] = [dict(item) for item in artifacts]
    value["jobs"] = [dict(item) for item in jobs]
    return value


def add_artifact(case_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    with db() as connection:
        connection.execute(
            "INSERT INTO module_zerlege_artifacts "
            "(id, case_id, original_name, kind, size_bytes, sha256, relative_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (artifact["artifact_id"], case_id, artifact["original_name"], artifact["kind"],
             artifact["size"], artifact["sha256"], artifact["relative_path"]),
        )
        row = connection.execute(
            "SELECT * FROM module_zerlege_artifacts WHERE id = ?", (artifact["artifact_id"],)
        ).fetchone()
    return dict(row)


def list_cases(project_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    with db() as connection:
        rows = connection.execute(
            "SELECT c.*, "
            "(SELECT COUNT(*) FROM module_zerlege_artifacts a WHERE a.case_id = c.id) AS artifact_count, "
            "(SELECT COUNT(*) FROM module_zerlege_jobs j WHERE j.case_id = c.id) AS job_count "
            "FROM module_zerlege_cases c WHERE c.project_id = ? "
            "ORDER BY c.created_at DESC, c.id DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    return [_case(row) for row in rows]


def get_artifact(artifact_id: str) -> dict[str, Any] | None:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM module_zerlege_artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
    return dict(row) if row else None


def list_artifacts(case_id: str) -> list[dict[str, Any]]:
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM module_zerlege_artifacts WHERE case_id = ? ORDER BY created_at, id",
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_job(job_id: str) -> dict[str, Any] | None:
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM module_zerlege_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    return dict(row) if row else None


def list_jobs(case_id: str) -> list[dict[str, Any]]:
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM module_zerlege_jobs WHERE case_id = ? ORDER BY created_at, id",
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def has_running_job(artifact_id: str, analysis_type: str) -> bool:
    """Laeuft fuer dieses Artefakt und diesen Typ schon eine Analyse?"""
    with db() as connection:
        row = connection.execute(
            "SELECT 1 FROM module_zerlege_jobs "
            "WHERE artifact_id = ? AND analysis_type = ? AND status IN ('queued', 'running') "
            "LIMIT 1",
            (artifact_id, analysis_type),
        ).fetchone()
    return row is not None


def create_job(case_id: str, artifact_id: str, analysis_type: str) -> dict[str, Any]:
    """Job anlegen. Doppelte laufende Jobs werden abgelehnt."""
    if has_running_job(artifact_id, analysis_type):
        raise ValueError("job already running")
    job_id = str(uuid.uuid4())
    with db() as connection:
        connection.execute(
            "INSERT INTO module_zerlege_jobs (id, case_id, artifact_id, analysis_type, status) "
            "VALUES (?, ?, ?, ?, 'queued')",
            (job_id, case_id, artifact_id, analysis_type),
        )
        row = connection.execute(
            "SELECT * FROM module_zerlege_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    return dict(row)


def update_job(job_id: str, **fields: Any) -> None:
    """Jobfelder aktualisieren. Erlaubt sind nur bekannte Spalten."""
    allowed = {"status", "progress", "result_path", "log_path", "error_code"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    assignments = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [job_id]
    with db() as connection:
        connection.execute(
            f"UPDATE module_zerlege_jobs SET {assignments}, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            values,
        )


def mark_interrupted_jobs() -> int:
    """Nach einem Neustart laufende Jobs als unterbrochen markieren."""
    with db() as connection:
        cursor = connection.execute(
            "UPDATE module_zerlege_jobs SET status = 'interrupted', "
            "error_code = 'reverse_job_interrupted', "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
            "WHERE status = 'running'"
        )
        return cursor.rowcount or 0


def next_queued_job() -> dict[str, Any] | None:
    """Naechsten wartenden Job holen."""
    with db() as connection:
        row = connection.execute(
            "SELECT * FROM module_zerlege_jobs WHERE status = 'queued' "
            "ORDER BY created_at, id LIMIT 1"
        ).fetchone()
    return dict(row) if row else None
