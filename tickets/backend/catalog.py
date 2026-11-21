"""Meldung an den Föderations-Katalog, wenn ein Ticket einen Task anlegt.

Spec: hydrahive2 ``docs/specs/federation-catalog.md`` §Katalog-Quellen.
``task_link.py`` schreibt direkt in ``module_tasks`` (Tasks-Modul). Die Quelle
``task`` stellt das Tasks-Modul; hier wird nur die Änderung gemeldet, damit der
neue Task sofort und nicht erst beim nächsten Timer-Lauf im Katalog ankommt.

Ältere Kerne ohne ``catalog_changed``: ``changed()`` tut nichts.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

TASK_KIND = "task"

_ctx: Any = None


def bind(ctx: Any) -> None:
    """In ``register(ctx)``: Kontext merken, wenn der Kern ``catalog_changed`` kennt."""
    global _ctx
    _ctx = ctx if callable(getattr(ctx, "catalog_changed", None)) else None


def changed(kind: str, username: str, item_id: str) -> None:
    """Nach erfolgreichem Schreiben aufrufen. Wirft nie."""
    ctx = _ctx
    if ctx is None:
        return
    try:
        ctx.catalog_changed(kind, username, item_id)
    except Exception as e:
        logger.debug("Tickets: catalog_changed ignoriert: %s", e)
