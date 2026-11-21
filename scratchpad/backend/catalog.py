"""Ideen als Katalog-Quelle für den Föderations-Katalog.

Spec: hydrahive2 ``docs/specs/federation-catalog.md`` §Katalog-Quellen. Der Kern
liest ``module_scratchpad_ideas`` nie direkt. Er nutzt diese vier Funktionen und
erfährt über ``changed()`` von jedem Schreiben.

Ältere Kerne kennen ``register_catalog_source`` und ``catalog_changed`` nicht.
Dann meldet sich das Modul nicht an, ``changed()`` tut nichts, und alles
andere läuft unverändert.

``updated_at`` bleibt der Wert, der in der Tabelle steht (mikrosekundengenau,
``…T10:00:00.500000Z``). Verglichen wird nur innerhalb der Ideen, nie mit Tasks.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

KIND = "idea"
TASK_KIND = "task"  # task_link.py legt einen Task an
MAX_TITLE = 300
MAX_LIMIT = 5000
_TABLE = "module_scratchpad_ideas"
_NOTES = "module_scratchpad_idea_notes"
_PROJECT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")  # Teil eines Dateipfads: nur dieses Muster
_COLUMNS = "id, username, title, status, project_id, created_at, updated_at"

_ctx: Any = None


def bind(ctx: Any) -> None:
    """In ``register(ctx)``: Kontext merken und, falls der Kern es kann, als Quelle anmelden."""
    global _ctx
    _ctx = ctx if callable(getattr(ctx, "catalog_changed", None)) else None
    register = getattr(ctx, "register_catalog_source", None)
    if callable(register):
        try:
            register(KIND, list_changed, list_versions, get_full, query)
        except Exception as e:  # der Kern wirft nie; abgesichert für Zwischenstände
            logger.warning("Ideen: Anmeldung als Katalog-Quelle fehlgeschlagen: %s", e)


def changed(username: str, item_id: str, kind: str = KIND) -> None:
    """Nach erfolgreichem Schreiben aufrufen. Wirft nie, auch ohne Kern-Unterstützung."""
    ctx = _ctx
    if ctx is None:
        return
    try:
        ctx.catalog_changed(kind, username, item_id)
    except Exception as e:
        logger.debug("Ideen: catalog_changed ignoriert: %s", e)


def _project_names(project_ids: set[str]) -> dict[str, str]:
    names: dict[str, str] = {}
    try:
        from hydrahive.projects import _config_io as projects
    except Exception:
        return names
    for pid in project_ids:
        if not pid or not _PROJECT_ID.match(pid):
            continue
        try:
            project = projects.get(pid)
        except Exception:
            project = None
        if project:
            names[pid] = project.get("name") or pid
    return names


def _metadata(rows: list[Any]) -> list[dict]:
    """Genau die Metadaten-Felder der Spec, ohne Text, Anmerkungen, Board, Herkunft."""
    names = _project_names({r["project_id"] for r in rows if r["project_id"]})
    return [{
        "kind": KIND,
        "item_id": r["id"],
        "owner": r["username"],
        "title": (r["title"] or "")[:MAX_TITLE],
        "status": r["status"],
        "priority": None,  # Ideen haben keine Priorität
        "project_id": r["project_id"],
        "project_name": names.get(r["project_id"]) if r["project_id"] else None,
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    } for r in rows]


def _limit(value: Any) -> int:
    return max(1, min(int(value), MAX_LIMIT))


def list_changed(username: str, after: tuple[str, str] | None, limit: int) -> list[dict]:
    """Einträge mit ``(updated_at, id) > after``, sortiert nach ``(updated_at, id)``."""
    sql = f"SELECT {_COLUMNS} FROM {_TABLE} WHERE username = ?"
    params: list[Any] = [username]
    if after is not None:
        stamp, item_id = after
        sql += " AND (updated_at > ? OR (updated_at = ? AND id > ?))"
        params += [stamp, stamp, item_id]
    sql += " ORDER BY updated_at, id LIMIT ?"
    params.append(_limit(limit))
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return _metadata(rows)


def list_versions(username: str) -> list[tuple[str, str, str | None]]:
    """``(item_id, updated_at, project_id)`` aller Ideen des Nutzers, für den Abgleich."""
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, updated_at, project_id FROM {_TABLE} WHERE username = ? ORDER BY id", (username,),
        ).fetchall()
    return [(r["id"], r["updated_at"], r["project_id"]) for r in rows]


def get_full(username: str, item_id: str) -> dict | None:
    """Metadaten plus Text und Anmerkungen (älteste zuerst). ``None`` bei fremder Idee."""
    with db() as conn:
        row = conn.execute(
            f"SELECT {_COLUMNS}, body FROM {_TABLE} WHERE username = ? AND id = ?", (username, item_id),
        ).fetchone()
        if row is None:
            return None
        notes = conn.execute(
            f"SELECT author, agent_name, body, created_at FROM {_NOTES} WHERE idea_id = ? ORDER BY created_at, id",
            (item_id,),
        ).fetchall()
    full = _metadata([row])[0]
    full["body"] = row["body"] or ""
    full["notes"] = [dict(n) for n in notes]
    return full


def query(usernames: list[str], project: str | None, status: str | None, q: str | None,
          limit: int, offset: int) -> list[dict]:
    """Eigene Ideen für die Katalog-Ansicht des Hubs, neueste Änderung zuerst."""
    users = [u for u in (usernames or []) if isinstance(u, str) and u]
    if not users:
        return []
    sql = f"SELECT {_COLUMNS} FROM {_TABLE} WHERE username IN ({', '.join('?' for _ in users)})"
    params: list[Any] = list(users)
    if project:
        sql += " AND project_id = ?"
        params.append(project)
    if status:
        sql += " AND status = ?"
        params.append(status)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND title LIKE ? ESCAPE '\\'"
        params.append(f"%{escaped}%")
    sql += " ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?"
    params += [_limit(limit), max(0, int(offset))]
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return _metadata(rows)
