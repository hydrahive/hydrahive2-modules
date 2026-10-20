"""Zugriff auf einen Fall = Projektrolle (wie storyteller/_files.project_access und der Kern check_project_access).

System-Admin darf alles, sonst zählt die Rolle im Projekt (read < write < admin). Ein Projekt ohne Fall ist für das
Modul „kein Fall“ (missing) – auch für Mitglieder.
"""
from __future__ import annotations

from hydrahive.db.connection import db


def _is_case(project_id: str) -> bool:
    with db() as c:
        return c.execute("SELECT 1 FROM module_legal_cases WHERE project_id = ? AND orphaned_at IS NULL",
                         (project_id,)).fetchone() is not None


def case_access(username: str, system_role: str, project_id: str, need: str) -> str:
    """'ok' | 'missing' (kein Fall/kein Mitglied → 404) | 'read_only' (Mitglied, Rolle reicht nicht → 403)."""
    from hydrahive.projects import _members_model
    from hydrahive.projects._config_io import get as get_project
    if not project_id or not _is_case(project_id):
        return "missing"
    project = get_project(project_id)
    if project is None:
        return "missing"
    if system_role == "admin":
        return "ok"
    role = _members_model.role_of(project, username)
    if role is None:
        return "missing"
    return "ok" if _members_model.has_at_least(role, need) else "read_only"
