"""Modul Diagramme (Spec diagramme/SPEC.md).

register(ctx) →
  - Router        /api/modules/diagramme/view-link/{id}
  - Geräte-Router /api/module-device/diagramme/sandbox/{id}?exp&sig  (ohne Login, signiert; nginx: Sandbox-CSP)
  - Werkzeuge     diagramm_erstellen, diagramm_hilfe
  - Migration     001_diagrams.sql
  - Skill         diagramme (System-Skill)
"""
from __future__ import annotations

import logging

from . import skill_sync, tools
from .device_routes import device_auth, device_router
from .routes import router

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    ctx.register_router(router)
    if hasattr(ctx, "register_device_router"):
        ctx.register_device_router(device_router, auth=device_auth)
    else:  # älterer Kern: Diagramme werden gespeichert, aber nicht im Chat angezeigt
        logger.warning("Diagramme: Kern ohne Geräte-Router – Ansicht im Chat nicht möglich (Update nötig)")
    for tool in tools.TOOLS:
        ctx.register_tool(tool)
    ctx.register_migrations("migrations")
    skill_sync.install()
