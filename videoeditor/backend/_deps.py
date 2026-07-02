"""Video-Editor — geteilte Route-Abhängigkeiten (Auth + Projekt-Guard).

Damit sich routes.py und audio_routes.py denselben Guard teilen, ohne ihn zu
duplizieren.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import storage

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def guard(user: str, project_id: str) -> None:
    """404 (nicht 403) für fremde/ungültige Projekte — Existenz nicht verraten."""
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")
