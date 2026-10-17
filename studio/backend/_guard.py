"""Zugriffsprüfung für alle Studio-Routen: nur Mitglieder des Projekts, sonst 404 (Projekt-ID wird geprüft)."""
from __future__ import annotations

import re

from hydrahive.api.middleware.errors import coded
from hydrahive.projects._config_io import list_for_user

_PROJECT_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def guard(user: str, project_id: str) -> None:
    if not _PROJECT_ID.match(project_id or "") or not any(p.get("id") == project_id for p in list_for_user(user)):
        raise coded(404, "studio_project_not_found")
