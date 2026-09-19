"""Permission-aware operational aggregates for the ticket inbox."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hydrahive.api.middleware.auth import AuthPrincipal
from hydrahive.db.connection import db

from .permissions import is_admin


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def dashboard_summary(principal: AuthPrincipal) -> dict[str, int | float | None]:
    now = _now()
    now_text = _iso(now)
    soon_text = _iso(now + timedelta(hours=24))
    with db() as conn:
        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM module_tickets GROUP BY status"
        ).fetchall()
        counts = {row["status"]: row["count"] for row in status_rows}
        params: tuple[str, ...]
        if is_admin(principal):
            team_clause = "1=1"
            params = ()
        else:
            team_clause = "team_id IN (SELECT team_id FROM module_ticket_team_members WHERE user_id=?)"
            params = (principal.user_id,)
        aggregates = conn.execute(
            f"""SELECT
                SUM(CASE WHEN due_at IS NOT NULL AND due_at < ? AND status NOT IN ('resolved','closed','cancelled') THEN 1 ELSE 0 END) AS overdue,
                SUM(CASE WHEN due_at IS NOT NULL AND due_at >= ? AND due_at <= ? AND status NOT IN ('resolved','closed','cancelled') THEN 1 ELSE 0 END) AS due_soon,
                SUM(CASE WHEN assigned_to IS NULL OR assigned_to='' THEN 1 ELSE 0 END) AS unassigned,
                SUM(CASE WHEN created_by=? OR assigned_to=? THEN 1 ELSE 0 END) AS mine,
                SUM(CASE WHEN {team_clause} THEN 1 ELSE 0 END) AS team,
                AVG(CASE WHEN first_response_at IS NOT NULL THEN
                    (julianday(first_response_at) - julianday(created_at)) * 86400.0 END) AS avg_first_response_seconds,
                AVG(CASE WHEN resolved_at IS NOT NULL THEN
                    (julianday(resolved_at) - julianday(created_at)) * 86400.0 END) AS avg_resolution_seconds
             FROM module_tickets""",
            (now_text, now_text, soon_text, principal.user_id, principal.user_id, *params),
        ).fetchone()
    result: dict[str, int | float | None] = {key: int(counts.get(key, 0)) for key in (
        "open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"
    )}
    result.update({
        "overdue": int(aggregates["overdue"] or 0),
        "due_soon": int(aggregates["due_soon"] or 0),
        "unassigned": int(aggregates["unassigned"] or 0),
        "mine": int(aggregates["mine"] or 0),
        "team": int(aggregates["team"] or 0),
        "avg_first_response_seconds": round(float(aggregates["avg_first_response_seconds"]), 1) if aggregates["avg_first_response_seconds"] is not None else None,
        "avg_resolution_seconds": round(float(aggregates["avg_resolution_seconds"]), 1) if aggregates["avg_resolution_seconds"] is not None else None,
    })
    return result
