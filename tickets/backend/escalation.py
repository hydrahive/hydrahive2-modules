"""Idempotent internal reminders for SLA and due-date breaches."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hydrahive.db.connection import db

from .notifications import notify_ticket_once


_ACTIVE = "status NOT IN ('resolved','closed','cancelled')"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def evaluate_escalations() -> int:
    now = _now()
    now_text = _iso(now)
    soon_text = _iso(now + timedelta(hours=24))
    created = 0
    with db(immediate=True) as conn:
        rows = conn.execute(
            f"SELECT id,response_due_at,resolution_due_at,due_at,first_response_at "
            f"FROM module_tickets WHERE {_ACTIVE}"
        ).fetchall()
        for row in rows:
            kinds: list[str] = []
            if row["due_at"] and row["due_at"] < now_text:
                kinds.append("overdue")
            elif row["due_at"] and row["due_at"] <= soon_text:
                kinds.append("due_soon")
            if row["response_due_at"] and not row["first_response_at"] and row["response_due_at"] < now_text:
                kinds.append("sla_response_breached")
            if row["resolution_due_at"] and row["resolution_due_at"] < now_text:
                kinds.append("sla_resolution_breached")
            for kind in kinds:
                created += int(notify_ticket_once(conn, row["id"], kind))
    return created
