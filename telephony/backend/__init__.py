"""Telefonie-Modul — ehrliches Walking Skeleton ohne SIP-Funktion.

Der Statusvertrag beweist Modulregistrierung und Authentifizierung. Alle
Telefoniefunktionen bleiben bis zu ihren jeweiligen SPEC-V1-Etappen deaktiviert.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

from .probe_models import SPIKE_PORT, SPIKE_REGISTRAR
from .probe_routes import router as probe_router

router = APIRouter()
router.include_router(probe_router)


@router.get("/status")
def status(
    _principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    """Liefert ausschließlich implementierte Fähigkeiten, keine Zukunftsbehauptungen."""
    return {
        "module": "telephony",
        "stage": "foundation",
        "status": "not_configured",
        "configured": False,
        "telephony_available": False,
        "probe_target": {
            "registrar": SPIKE_REGISTRAR,
            "port": SPIKE_PORT,
        },
        "features": {
            "setup": False,
            "registration_probe": True,
            "inbound_calls": False,
            "outbound_calls": False,
            "archive": False,
        },
    }


def register(ctx) -> None:
    """Registriert nur den authentifizierten Statusrouter."""
    ctx.register_router(router)
