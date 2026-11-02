"""Projektgrenze der Zerlege-Werkstatt; unberechtigte Projekte bleiben unsichtbar."""
from __future__ import annotations

from fastapi import HTTPException

from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from hydrahive.projects import config as project_config


def require_project(username: str, role: str, project_id: str, *, required: str = "read") -> dict:
    project = project_config.get(project_id)
    if not project:
        raise coded(404, "reverse_project_not_found")
    try:
        check_project_access(project, username, role, required)
    except HTTPException:
        raise coded(404, "reverse_project_not_found") from None
    return project
