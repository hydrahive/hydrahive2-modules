"""Schnittstellen /api/modules/vibe (PLAN-V1.md). Nur Admins.

Baustein 1: nur `GET /state`. Projekte anlegen/entfernen kommen mit Baustein 4.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal

from . import incus, state

router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]


@router.get("/state")
def get_state(p: Admin) -> dict:
    """Ohne incus (z. B. Mac ohne Colima) kein Fehler, sondern ein Zustand, den die Seite erklären kann."""
    if not incus.available():
        return {"incus": False, "error_code": "vibe_no_incus", "projects": []}
    return {"incus": True, "error_code": "", "projects": state.projects_of(p.username)}
