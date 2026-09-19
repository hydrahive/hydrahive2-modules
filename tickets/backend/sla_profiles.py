"""Admin CRUD for editable ticket SLA profiles."""
from __future__ import annotations

from uuid import uuid4

from hydrahive.db.connection import db

from .models import SlaProfileCreate, SlaProfileUpdate

_FIELDS = (
    "name", "description", "active", "urgent_response_hours", "urgent_resolution_hours",
    "high_response_hours", "high_resolution_hours", "normal_response_hours",
    "normal_resolution_hours", "low_response_hours", "low_resolution_hours",
)
_CREATE_FIELDS = tuple(field for field in _FIELDS if field != "active")


def _row(row) -> dict:
    return dict(row) if row else {}


def list_profiles() -> list[dict]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM module_ticket_sla_profiles ORDER BY name ASC").fetchall()
    return [_row(row) for row in rows]


def create_profile(body: SlaProfileCreate) -> dict:
    profile_id = str(uuid4())
    values = body.model_dump()
    with db(immediate=True) as conn:
        try:
            conn.execute(
                "INSERT INTO module_ticket_sla_profiles "
                f"(id,{','.join(_CREATE_FIELDS)}) VALUES ({','.join('?' for _ in range(len(_CREATE_FIELDS) + 1))})",
                (profile_id, *[values[field] for field in _CREATE_FIELDS]),
            )
        except Exception as exc:
            raise ValueError("sla_profile_conflict") from exc
        return _row(conn.execute("SELECT * FROM module_ticket_sla_profiles WHERE id=?", (profile_id,)).fetchone())


def update_profile(profile_id: str, body: SlaProfileUpdate) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes:
        changes["name"] = changes["name"].strip()
        if not changes["name"]:
            raise ValueError("invalid_sla_profile_name")
    if not changes:
        raise ValueError("empty_sla_update")
    assignments = [f"{field}=?" for field in changes if field in _FIELDS]
    args = [changes[field] for field in changes if field in _FIELDS]
    if not assignments:
        raise ValueError("empty_sla_update")
    with db(immediate=True) as conn:
        if conn.execute("SELECT 1 FROM module_ticket_sla_profiles WHERE id=?", (profile_id,)).fetchone() is None:
            raise KeyError("sla_profile_not_found")
        assignments.append("updated_at=strftime('%Y-%m-%dT%H:%M:%SZ', 'now')")
        try:
            conn.execute(
                f"UPDATE module_ticket_sla_profiles SET {','.join(assignments)} WHERE id=?",
                (*args, profile_id),
            )
        except Exception as exc:
            raise ValueError("sla_profile_conflict") from exc
        return _row(conn.execute("SELECT * FROM module_ticket_sla_profiles WHERE id=?", (profile_id,)).fetchone())
