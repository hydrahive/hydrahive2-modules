from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any


def _json(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, sqlite3.Row):
        value = dict(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_default)


def _default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def record(
    conn: sqlite3.Connection,
    household_id: int,
    actor_user_id: str,
    entity_type: str,
    entity_id: int | str,
    action: str,
    before: Any = None,
    after: Any = None,
) -> None:
    conn.execute(
        "INSERT INTO module_haushaltsbuch_audit_events "
        "(household_id, actor_user_id, entity_type, entity_id, action, before_json, after_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            household_id,
            actor_user_id,
            entity_type,
            str(entity_id),
            action,
            _json(before),
            _json(after),
        ),
    )


def decode_row(row: sqlite3.Row) -> dict:
    result = dict(row)
    result["before"] = (
        json.loads(result.pop("before_json")) if result["before_json"] else None
    )
    result["after"] = (
        json.loads(result.pop("after_json")) if result["after_json"] else None
    )
    return result
