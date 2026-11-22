"""Fremde Tasks anderer Instanzen (Gemeinsame Taskpflege).

Spec: hydrahive2 ``docs/specs/federation-shared-tasks.md`` §Anzeige in den Modulen.
Das Modul liest keine Kerntabellen. Es nutzt ``ctx.catalog_foreign_list`` und
``ctx.catalog_foreign_get``. Beide werfen nie und liefern ohne Gemeinsame
Taskpflege ``[]`` bzw. ``None``.

Ältere Kerne kennen die Methoden nicht. Dann zeigt das Modul einfach keine
fremden Einträge (Prüfung mit ``callable(getattr(...))`` wie bei
``catalog_changed``).

Der Nutzername kommt immer vom angemeldeten Nutzer (Aufrufer übergibt
``auth[0]``), nie aus Request-Parametern.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

KIND = "task"
ALL = "*"
PAGE = 500                 # Obergrenze je Aufruf im Kern
MAX_PAGES = 10             # höchstens 5000 fremde Einträge je Liste
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

_ctx: Any = None


def bind(ctx: Any) -> None:
    """In ``register(ctx)``: Kontext nur merken, wenn der Kern fremde Einträge kennt."""
    global _ctx
    _ctx = ctx if callable(getattr(ctx, "catalog_foreign_list", None)) else None


def available() -> bool:
    return _ctx is not None


def list_foreign(username: str, *, project_id: str | None, status: str | None) -> list[dict[str, Any]]:
    """Fremde Tasks des Nutzers. ``project_id`` = eigene Projekt-ID (nach Zuordnung),
    ``None`` = alle zugeordneten und die ohne Projekt. Wirft nie."""
    ctx = _ctx
    if ctx is None:
        return []
    scope = project_id or ALL
    statuses = [status] if status else None
    out: list[dict[str, Any]] = []
    try:
        for page in range(MAX_PAGES):
            rows = ctx.catalog_foreign_list(KIND, username, scope, statuses, None, PAGE, page * PAGE)
            if not isinstance(rows, list):
                break
            out += [{**r, "foreign": True} for r in rows if isinstance(r, dict) and r.get("owner") == username]
            if len(rows) < PAGE:
                break
    except Exception as e:  # der Kern wirft nie; abgesichert für Zwischenstände
        logger.warning("Tasks: fremde Einträge nicht lesbar: %s", e)
        return []
    return out


async def get_foreign(username: str, origin_fp: str, item_id: str) -> dict[str, Any] | None:
    """Volltext eines fremden Tasks. ``None`` = nicht sichtbar oder alter Kern. Wirft nie."""
    ctx = _ctx
    get = getattr(ctx, "catalog_foreign_get", None) if ctx is not None else None
    if not callable(get):
        return None
    try:
        full = await get(KIND, username, origin_fp, item_id)
    except Exception as e:
        logger.warning("Tasks: Volltext eines fremden Eintrags nicht lesbar: %s", e)
        return None
    if not isinstance(full, dict) or not isinstance(full.get("item"), dict):
        return None
    if full["item"].get("owner") not in (None, username):
        return None
    return full


def _sort_key(entry: dict[str, Any]) -> tuple:
    return (_PRIORITY_ORDER.get(entry.get("priority") or "", 2), entry.get("created_at") or "",
            entry.get("id") or entry.get("item_id") or "")


def merge(own: list[dict[str, Any]], foreign: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Eigene und fremde zusammen, sortiert wie die eigene Liste (Priorität, angelegt, ID)."""
    if not foreign:
        return own
    return sorted([*own, *foreign], key=_sort_key)
