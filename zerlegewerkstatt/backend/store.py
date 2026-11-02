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


def list_cases(project_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM module_zerlege_cases WHERE project_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (project_id, limit),
        ).fetchall()
    return [_case(row) for row in rows]
