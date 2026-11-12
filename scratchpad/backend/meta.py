"""Stammdaten für die Oberfläche: Statusliste, Grenzen, vorhandene Nachbarmodule."""
from __future__ import annotations

from hydrahive.db.connection import db

from . import store, task_link

_BOARDS_TABLE = "module_blueprint_boards"


def table_exists(name: str) -> bool:
    with db() as conn:
        return conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone() is not None


def describe() -> dict:
    return {
        "statuses": list(store.STATUSES),
        "open_statuses": list(store.OPEN_STATUSES),
        "tasks_installed": task_link.installed(),
        "blueprint_installed": table_exists(_BOARDS_TABLE),
        "limits": {"title": store.MAX_TITLE, "body": store.MAX_BODY, "ideas": store.MAX_IDEAS},
    }
