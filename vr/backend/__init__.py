"""VR-Modul — Agenten sprechen die HydraVR-Brille ihres Nutzers an.

Spec: hydravr-quest/docs/specs/vr-modul.md. Werkzeuge: vr_say, vr_notify,
vr_open_app, vr_status. Die Brille hört über SSE (/api/modules/vr/events) mit.
Alles im Speicher, keine Datenbank.
"""
from __future__ import annotations

from .routes import router
from .tools import TOOLS


def register(ctx) -> None:
    ctx.register_router(router)
    for tool in TOOLS:
        ctx.register_tool(tool)
