"""Internal polling notifications; no email or external push channel."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from hydrahive.db.connection import db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def notify_ticket(
    conn: sqlite3.Connection, ticket_id: str, actor_user_id: str | None, kind: str
) -> None:
    ticket = conn.execute(
        "SELECT created_by,assigned_to,team_id FROM module_tickets WHERE id=?", (ticket_id,)
    ).fetchone()
    if ticket is None:
        return
    recipients = {ticket["created_by"], ticket["assigned_to"]}
    if ticket["team_id"]:
        recipients.update(
            row["user_id"] for row in conn.execute(
                "SELECT user_id FROM module_ticket_team_members WHERE team_id=?",
                (ticket["team_id"],),
            ).fetchall()
        )
    recipients.discard(None)
    if actor_user_id:
        recipients.discard(actor_user_id)
    conn.executemany(
        "INSERT INTO module_ticket_notifications(id,user_id,ticket_id,kind) VALUES(?,?,?,?)",
        ((str(uuid4()), user_id, ticket_id, kind) for user_id in recipients),
    )


def notify_ticket_once(
    conn: sqlite3.Connection, ticket_id: str, kind: str,
) -> bool:
    """Create one notification for a ticket/kind for idempotent escalations."""
    exists = conn.execute(
        "SELECT 1 FROM module_ticket_notifications WHERE ticket_id=? AND kind=? LIMIT 1",
        (ticket_id, kind),
    ).fetchone()
    if exists is not None:
        return False
    notify_ticket(conn, ticket_id, None, kind)
    return True


def list_for_user(user_id: str, *, unread_only: bool = True, limit: int = 50) -> list[dict]:
    clause = "AND n.read_at IS NULL" if unread_only else ""
    with db() as conn:
        rows = conn.execute(
            "SELECT n.id,n.user_id,n.ticket_id,n.kind,n.read_at,n.created_at,t.number,t.title "
            "FROM module_ticket_notifications n JOIN module_tickets t ON t.id=n.ticket_id "
            f"WHERE n.user_id=? {clause} ORDER BY n.created_at DESC, n.rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_read(user_id: str, notification_id: str) -> bool:
    with db(immediate=True) as conn:
        cursor = conn.execute(
            "UPDATE module_ticket_notifications SET read_at=? WHERE id=? AND user_id=? AND read_at IS NULL",
            (_now(), notification_id, user_id),
        )
    return cursor.rowcount > 0
