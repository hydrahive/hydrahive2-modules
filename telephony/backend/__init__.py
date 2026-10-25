"""Telefonie-Modul — Etappe 1 (SIP-Verbindung), 2 (Anrufe annehmen: Ansage, Telefon-Assistent) und 3 (selbst anrufen,
PLAN-ANRUFEN-3.md).

Der Status meldet nur, was es gibt. Archiv folgt (SPEC-V1). Die Spike-Routen (/spike/*) bleiben Entwicklerwerkzeug.
"""
from __future__ import annotations

import atexit
from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

from . import connections
from .calls_routes import router as calls_router
from .conn_routes import router as conn_router
from .probe_routes import router as probe_router

router = APIRouter()
router.include_router(probe_router)
router.include_router(conn_router)
router.include_router(calls_router)


@router.get("/status")
def status(
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    """Liefert ausschließlich implementierte Fähigkeiten, keine Zukunftsbehauptungen."""
    conn = connections.public(principal.user_id)
    return {
        "module": "telephony",
        "stage": "connection",
        "status": conn["status"],
        "configured": conn["configured"],
        "telephony_available": False,
        "features": {
            "setup": True,
            "registration": True,
            "inbound_calls": True,
            "outbound_calls": True,
            "archive": False,
        },
    }


RECONCILE_SECONDS = 60


def register(ctx) -> None:
    """Router, Datenbank und den Job, der gespeicherte Verbindungen angemeldet hält (auch nach Neustart)."""
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    ctx.register_job("connections", _reconcile, interval_seconds=RECONCILE_SECONDS, initial_delay_seconds=10)
    _register_butler(ctx)


def _register_butler(ctx) -> None:
    """Butler „Anruf kommt rein“ (PLAN-BUTLER B1). Ältere Kerne ohne Butler-Brücke: still auslassen."""
    if not hasattr(ctx, "register_butler_trigger"):
        return
    from . import butler_specs

    for spec in butler_specs.TRIGGERS:
        ctx.register_butler_trigger(spec)
    for spec in butler_specs.CONDITIONS:
        ctx.register_butler_condition(spec)
    for spec in butler_specs.ACTIONS:
        ctx.register_butler_action(spec)
    atexit.register(connections.MANAGER.stop_all)      # beim Beenden abmelden (sonst verfällt es nach Ablaufzeit)


async def _reconcile() -> None:
    import asyncio

    await asyncio.to_thread(connections.reconcile)
