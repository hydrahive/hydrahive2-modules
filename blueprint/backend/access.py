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
