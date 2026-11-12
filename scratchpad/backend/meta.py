"""Stammdaten für die Oberfläche: Statusliste, Grenzen, vorhandene Nachbarmodule."""
from __future__ import annotations

from . import board_link, store, task_link


def describe() -> dict:
    return {
        "statuses": list(store.STATUSES),
        "open_statuses": list(store.OPEN_STATUSES),
        "tasks_installed": task_link.installed(),
        "blueprint_installed": board_link.installed(),
        "limits": {"title": store.MAX_TITLE, "body": store.MAX_BODY, "ideas": store.MAX_IDEAS},
    }
