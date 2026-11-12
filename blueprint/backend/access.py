"""Projektzugriff für Boards.

Ein Board darf nur einem Projekt zugeordnet werden, das der Nutzer sehen darf
(Mitglied, Ersteller oder System-Admin). Fremde und unbekannte Projekte liefern
denselben Fehler, damit sich Projekt-IDs nicht erraten lassen.
"""
from __future__ import annotations

import re

from hydrahive.projects import _config_io as projects
from hydrahive.projects import _members_model

from .store import BoardError

# Die ID wird Teil eines Dateipfads (projects/<id>/config.json): nur dieses Muster zulassen.
_PROJECT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def check_project(username: str, role: str, project_id: str | None) -> str | None:
    """Liefert die geprüfte Projekt-ID oder ``None`` für „ohne Projekt“."""
    wanted = (project_id or "").strip()
    if not wanted:
        return None
    project = projects.get(wanted) if _PROJECT_ID.match(wanted) else None
    if project is None:
        raise BoardError("project_not_found")
    if role != "admin" and _members_model.role_of(project, username) is None:
        raise BoardError("project_not_found")
    return wanted


def system_role(username: str) -> str:
    """Aktuelle Systemrolle eines Nutzers. Werkzeuge kennen nur den Namen, nicht die Rolle."""
    from hydrahive.api.middleware.users import get_by_username

    user = get_by_username(username) if username else None
    return user["role"] if user else "user"


def session_project(username: str, project_id: str | None) -> str | None:
    """Projekt der Sitzung für ein neues Board. ``None``, wenn der Nutzer es nicht sehen darf."""
    try:
        return check_project(username, system_role(username), project_id)
    except BoardError:
        return None


def project_state(username: str, role: str, project_id: str | None) -> tuple[dict | None, str]:
    """Projekt und was der Nutzer dort darf: ``ok`` (Schreibrecht), ``read_only`` oder ``missing``.

    ``missing`` gilt für unbekannte Projekte genauso wie für solche, in denen der Nutzer kein Mitglied ist.
    """
    wanted = (project_id or "").strip()
    project = projects.get(wanted) if _PROJECT_ID.match(wanted) else None
    if project is None:
        return None, "missing"
    if role == "admin":
        return project, "ok"
    member = _members_model.role_of(project, username)
    if member is None:
        return None, "missing"
    return project, "ok" if _members_model.has_at_least(member, "write") else "read_only"
