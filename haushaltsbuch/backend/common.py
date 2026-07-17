from __future__ import annotations

import sqlite3
from datetime import date
from typing import Any

NOW = "strftime('%Y-%m-%dT%H:%M:%fZ','now')"


def as_dict(row: sqlite3.Row) -> dict:
    result = dict(row)
    for key in ("archived", "internal", "active"):
        if key in result:
            result[key] = bool(result[key])
    return result


def model_values(model: Any, *, exclude: set[str] | None = None) -> dict:
    values = model.model_dump(exclude=exclude or set())
    return {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in values.items()
    }
