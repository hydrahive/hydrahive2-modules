"""Ablage der Diagramme (Spec §5a): alles bleibt gespeichert, Fassungen, Papierkorb, Rechte.

Dateien: data_dir/diagramme/<id>/diagramm.html + eingabe.json|eingabe.md. Liste in Tabelle module_diagrams.
Nie automatisch löschen; endgültiges Löschen kommt erst mit der Oberfläche (S2) und nur durch Menschen.
"""
from __future__ import annotations

import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.db.connection import db

ID_RE = re.compile(r"^d_[A-Za-z0-9_-]{1,62}$")
_COLS = "id, username, project_id, session_id, agent_id, title, kind, created_at, version_of, deleted_at"


def root() -> Path:
    from hydrahive.settings import settings
    return settings.data_dir / "diagramme"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _new_id() -> str:
    return f"d_{int(time.time() * 1000):x}{secrets.token_hex(5)}"


def _row(r: Any) -> dict[str, Any]:
    return dict(zip(_COLS.split(", "), r))


def get(view_id: str) -> dict[str, Any] | None:
    if not isinstance(view_id, str) or not ID_RE.match(view_id):
        return None
    with db() as c:
        r = c.execute(f"SELECT {_COLS} FROM module_diagrams WHERE id = ?", (view_id,)).fetchone()
    return _row(r) if r else None


def _origin(view_id: str) -> str:
    """Erste Fassung einer Kette (version_of zeigt immer auf sie)."""
    row = get(view_id)
    return row["version_of"] or row["id"] if row else view_id


def create(*, username: str, project_id: str | None, session_id: str | None, agent_id: str | None, title: str,
           kind: str, html: str, source: str, source_ext: str, version_of: str | None = None) -> dict[str, Any]:
    view_id = _new_id()
    folder = root() / view_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "diagramm.html").write_text(html, encoding="utf-8")
    (folder / f"eingabe.{'md' if source_ext == 'md' else 'json'}").write_text(source, encoding="utf-8")
    origin = _origin(version_of) if version_of else None
    with db() as c:
        c.execute(f"INSERT INTO module_diagrams ({_COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                  (view_id, username, project_id, session_id, agent_id, title, kind, _now(), origin))
    return get(view_id) or {}


def html(view_id: str) -> str | None:
    if get(view_id) is None:
        return None
    path = root() / view_id / "diagramm.html"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def versions(view_id: str) -> list[dict[str, Any]]:
    origin = _origin(view_id)
    with db() as c:
        rows = c.execute(f"SELECT {_COLS} FROM module_diagrams WHERE id = ? OR version_of = ? "
                         "ORDER BY created_at, rowid", (origin, origin)).fetchall()
    return [_row(r) for r in rows]


def trash(view_id: str) -> None:
    with db() as c:
        c.execute("UPDATE module_diagrams SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL", (_now(), view_id))


def restore(view_id: str) -> None:
    with db() as c:
        c.execute("UPDATE module_diagrams SET deleted_at = NULL WHERE id = ?", (view_id,))


def _member_projects(username: str) -> set[str]:
    from hydrahive.projects._config_io import list_for_user
    return {p.get("id") for p in list_for_user(username) if p.get("id")}


def can_view(row: dict[str, Any] | None, username: str, role: str) -> bool:
    if not row:
        return False
    if role == "admin" or row["username"] == username:
        return True
    return bool(row["project_id"]) and row["project_id"] in _member_projects(username)


def list_for(username: str, role: str) -> list[dict[str, Any]]:
    """Sichtbare Diagramme ohne Papierkorb, neueste zuerst (Sammlung kommt in S2)."""
    with db() as c:
        rows = c.execute(f"SELECT {_COLS} FROM module_diagrams WHERE deleted_at IS NULL "
                         "ORDER BY created_at DESC, rowid DESC").fetchall()
    return [d for d in (_row(r) for r in rows) if can_view(d, username, role)]
