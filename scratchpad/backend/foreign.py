"""Fremde Ideen anderer Instanzen (Gemeinsame Taskpflege).

Spec: hydrahive2 ``docs/specs/federation-shared-tasks.md`` §Anzeige in den Modulen.
Das Modul liest keine Kerntabellen. Es nutzt ``ctx.catalog_foreign_list`` und
``ctx.catalog_foreign_get``. Beide werfen nie und liefern ohne Gemeinsame
Taskpflege ``[]`` bzw. ``None``.

Ältere Kerne kennen die Methoden nicht. Dann zeigt das Modul einfach keine
fremden Ideen (Prüfung mit ``callable(getattr(...))`` wie bei ``catalog_changed``).

Der Nutzername kommt immer vom angemeldeten Nutzer (Aufrufer übergibt den
Nutzer aus ``require_auth``), nie aus Request-Parametern.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

KIND = "idea"
ALL = "*"
NO_PROJECT = "none"        # Filterwert des Moduls für „ohne Projekt“
PAGE = 500                 # Obergrenze je Aufruf im Kern
MAX_PAGES = 10             # höchstens 5000 fremde Ideen je Liste

_ctx: Any = None


def bind(ctx: Any) -> None:
    """In ``register(ctx)``: Kontext nur merken, wenn der Kern fremde Einträge kennt."""
    global _ctx
    _ctx = ctx if callable(getattr(ctx, "catalog_foreign_list", None)) else None


def available() -> bool:
    return _ctx is not None


def _scope(project: str | None) -> str | None:
    """Projektfilter des Moduls → Kern: alle (``*``), nur ohne Projekt (``None``), eigene ID."""
    if not project:
        return ALL
    return None if project == NO_PROJECT else project


def list_foreign(username: str, *, project: str | None,
                 statuses: tuple[str, ...] | None) -> list[dict[str, Any]]:
    """Fremde Ideen des Nutzers, Projekt- und Statusfilter wie bei den eigenen. Wirft nie."""
    ctx = _ctx
    if ctx is None:
        return []
    scope = _scope(project)
    wanted = list(statuses) if statuses else None
    out: list[dict[str, Any]] = []
    try:
        for page in range(MAX_PAGES):
            rows = ctx.catalog_foreign_list(KIND, username, scope, wanted, None, PAGE, page * PAGE)
            if not isinstance(rows, list):
                break
            out += [{**r, "foreign": True} for r in rows if isinstance(r, dict) and r.get("owner") == username]
            if len(rows) < PAGE:
                break
    except Exception as e:  # der Kern wirft nie; abgesichert für Zwischenstände
        logger.warning("Ideen: fremde Einträge nicht lesbar: %s", e)
        return []
    return out


async def get_foreign(username: str, origin_fp: str, item_id: str) -> dict[str, Any] | None:
    """Volltext einer fremden Idee (Text und Anmerkungen). ``None`` = nicht sichtbar oder alter Kern."""
    ctx = _ctx
    get = getattr(ctx, "catalog_foreign_get", None) if ctx is not None else None
    if not callable(get):
        return None
    try:
        full = await get(KIND, username, origin_fp, item_id)
    except Exception as e:
        logger.warning("Ideen: Volltext einer fremden Idee nicht lesbar: %s", e)
        return None
    if not isinstance(full, dict) or not isinstance(full.get("item"), dict):
        return None
    if full["item"].get("owner") != username:            # zweite Schranke, auch ohne owner (Review #456)
        return None
    return full


def _stamp(value: str | None) -> str:
    """Zeitstempel vergleichbar machen: eigene mit Mikrosekunden, fremde sekundengenau."""
    value = value or ""
    return value[:19] + (value[19:].rstrip("Z") or ".000000")[:7].ljust(7, "0")


def merge(own: list[dict[str, Any]], foreign: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Eigene und fremde zusammen, sortiert wie die eigene Liste (neueste Änderung zuerst)."""
    if not foreign:
        return own
    items = sorted([*own, *foreign], key=lambda e: e.get("id") or e.get("item_id") or "")
    return sorted(items, key=lambda e: _stamp(e.get("updated_at")), reverse=True)


def add_counts(counts: dict[str, int], foreign: list[dict[str, Any]]) -> dict[str, int]:
    """Zähler je Status um die fremden Ideen ergänzen (nur bekannte Status)."""
    total = dict(counts)
    for entry in foreign:
        status = entry.get("status")
        if status in total:
            total[status] += 1
    return total
