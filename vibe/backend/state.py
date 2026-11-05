"""Zustand und Projektliste des Moduls Vibe (Tabelle module_vibe_projects)."""
from __future__ import annotations

from hydrahive.db.connection import db

_PUBLIC = ("project_id", "name", "state", "progress", "error_code", "error_step", "heal_enabled", "last_used_at",
           "created_at")
_ALL = ("project_id", "agent_id", "container", "name", "owner", "state", "progress", "error_code", "error_step",
        "heal_enabled", "last_used_at", "created_at")


def projects_of(owner: str) -> list[dict]:
    """Nur die eigenen Projekte, nur Felder, die die Oberfläche braucht (kein Container-Name, keine Agenten-ID)."""
    with db() as conn:
        rows = conn.execute(f"SELECT {', '.join(_PUBLIC)} FROM module_vibe_projects WHERE owner = ? "
                            "ORDER BY created_at, project_id", (owner,)).fetchall()
    out = [dict(zip(_PUBLIC, r, strict=True)) for r in rows]
    for p in out:
        p["heal_enabled"] = bool(p["heal_enabled"])
    return out


def get_row(project_id: str) -> dict | None:
    """Volle Zeile (mit Container und Agent) – nur für das Modul selbst, nie nach außen geben."""
    with db() as conn:
        r = conn.execute(f"SELECT {', '.join(_ALL)} FROM module_vibe_projects WHERE project_id = ?",
                         (project_id,)).fetchone()
    if r is None:
        return None
    row = dict(zip(_ALL, r, strict=True))
    row["heal_enabled"] = bool(row["heal_enabled"])
    return row


def add_row(*, project_id: str, agent_id: str, container: str, name: str, owner: str) -> None:
    with db() as conn:
        conn.execute("INSERT INTO module_vibe_projects (project_id, agent_id, container, name, owner) "
                     "VALUES (?, ?, ?, ?, ?)", (project_id, agent_id, container, name, owner))
        conn.commit()


def set_state(project_id: str, value: str, *, error_code: str = "", error_step: str = "") -> None:
    """Zustand setzen. Fehlergrund nur bei `failed`; jeder andere Zustand löscht ihn, `ready` auch den Fortschritt."""
    with db() as conn:
        conn.execute("UPDATE module_vibe_projects SET state = ?, error_code = ?, error_step = ?, "
                     "progress = CASE WHEN ? = 'ready' THEN '' ELSE progress END WHERE project_id = ?",
                     (value, error_code, error_step, value, project_id))
        conn.commit()


def set_progress(project_id: str, step: str) -> None:
    with db() as conn:
        conn.execute("UPDATE module_vibe_projects SET progress = ? WHERE project_id = ?", (step, project_id))
        conn.commit()


def set_heal(project_id: str, enabled: bool) -> None:
    with db() as conn:
        conn.execute("UPDATE module_vibe_projects SET heal_enabled = ? WHERE project_id = ?", (int(bool(enabled)), project_id))
        conn.commit()


def all_rows() -> list[dict]:
    with db() as conn:
        ids = [r[0] for r in conn.execute("SELECT project_id FROM module_vibe_projects ORDER BY created_at")]
    return [r for r in (get_row(i) for i in ids) if r]


def delete_row(project_id: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM module_vibe_projects WHERE project_id = ?", (project_id,))
        conn.commit()
