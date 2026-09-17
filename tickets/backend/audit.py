"""Append-only audit event persistence for ticket mutations."""
from __future__ import annotations

import json
import sqlite3
from typing import Any
from uuid import uuid4

from hydrahive.db.connection import db


def record_event(
    conn: sqlite3.Connection,
    ticket_id: str,
    actor_id: str,
    actor_kind: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    conn.execute(
        "INSERT INTO module_ticket_events "
        "(id,ticket_id,actor_id,actor_kind,event_type,payload_json) VALUES (?,?,?,?,?,?)",
        (
            str(uuid4()), ticket_id, actor_id, actor_kind, event_type,
            json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
        ),
    )


def list_events(ticket_id: str, *, limit: int = 100) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM module_ticket_events WHERE ticket_id=? ORDER BY rowid ASC LIMIT ?",
            (ticket_id, limit),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        result.append(item)
    return result
