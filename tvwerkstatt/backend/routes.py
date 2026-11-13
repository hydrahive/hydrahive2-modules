"""Schnittstellen /api/modules/tvwerkstatt (PLAN-E1.md). Nur Admins.

Fehler kommen als Code (`tvw_…`), nie als Text mit Pfaden oder Ausgaben vom Server.
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
    """Ohne incus kein Fehler, sondern ein Zustand, den die Seite erklären kann."""
    if not incus.available():
        return {"incus": False, "error_code": "tvw_no_incus", "devices": [], "builds": []}
    return {"incus": True, "error_code": "", "devices": state.devices(), "builds": state.builds()}
