"""Projektzugriff für Ideen.

Eine Idee darf nur einem Projekt zugeordnet werden, das der Nutzer sehen darf
(Mitglied, Ersteller oder System-Admin). Fremde und unbekannte Projekte liefern
denselben Fehler, damit sich Projekt-IDs nicht erraten lassen.
"""
from __future__ import annotations

import re

from hydrahive.projects import _members_model
from hydrahive.projects import _config_io as projects

from .store import IdeaError

# Die ID wird Teil eines Dateipfads (projects/<id>/config.json): nur dieses Muster zulassen.
_PROJECT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def check_project(username: str, role: str, project_id: str | None) -> str | None:
    """Liefert die geprüfte Projekt-ID oder ``None`` für „ohne Projekt“."""
    wanted = (project_id or "").strip()
    if not wanted:
        return None
    project = projects.get(wanted) if _PROJECT_ID.match(wanted) else None
    if project is None:
        raise IdeaError("project_not_found")
    if role != "admin" and _members_model.role_of(project, username) is None:
        raise IdeaError("project_not_found")
    return wanted


def system_role(username: str) -> str:
    """Aktuelle Systemrolle eines Nutzers. Werkzeuge kennen nur den Namen, nicht die Rolle."""
    from hydrahive.api.middleware.users import get_by_username

    user = get_by_username(username) if username else None
    return user["role"] if user else "user"


def project_names(username: str, role: str) -> dict[str, str]:
    """Projekt-ID → Name für alles, was der Nutzer sehen darf (für Anzeige und Werkzeug-Text)."""
    visible = projects.list_all() if role == "admin" else projects.list_for_user(username)
    return {p["id"]: p.get("name") or p["id"] for p in visible if p.get("id")}
