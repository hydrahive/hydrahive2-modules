"""VR-Modul — Agenten sprechen die HydraVR-Brille ihres Nutzers an.

Spec: hydravr-quest/docs/specs/vr-modul.md. Werkzeuge: vr_say, vr_notify,
vr_open_app, vr_status. Die Brille hört über SSE (/api/modules/vr/events) mit.
Ereignisse und Fensterstand nur im Speicher; Kopplung (Codes, Brillen) in eigener Tabelle.
"""
from __future__ import annotations

import logging

from .pair_routes import device_auth, device_router
from .pair_routes import router as pair_router
from .routes import router
from .tools import TOOLS

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_router(pair_router)
    if hasattr(ctx, "register_device_router"):
        ctx.register_device_router(device_router, auth=device_auth)
    else:  # älterer Kern: alles geht, nur Koppeln per QR nicht
        logger.warning("VR: Kern ohne Geräte-Router – Koppeln per QR nicht verfügbar (Update nötig)")
    for tool in TOOLS:
        ctx.register_tool(tool)
    ctx.register_migrations("migrations")
