"""Zustand und Projektliste des Moduls Vibe (Tabelle module_vibe_projects)."""
from __future__ import annotations

from hydrahive.db.connection import db

_PUBLIC = ("project_id", "name", "state", "heal_enabled", "last_used_at", "created_at")


def projects_of(owner: str) -> list[dict]:
    """Nur die eigenen Projekte, nur Felder, die die Oberfläche braucht (kein Container-Name, keine Agenten-ID)."""
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(_PUBLIC)} FROM module_vibe_projects WHERE owner = ? "
                            "ORDER BY created_at, project_id", (owner,)).fetchall()
    out = [dict(zip(_PUBLIC, r, strict=True)) for r in rows]
    for p in out:
        p["heal_enabled"] = bool(p["heal_enabled"])
    return out
