"""Modul Vibe – beschreiben, ansehen, weitermachen (SPEC.md, PLAN-V1.md).

Baustein 1: Gerüst, Zugriff nur für Admins, Zustand. Container, Agent, Zeitleiste und Vorschau folgen mit den
weiteren Bausteinen des Plans.
"""
from __future__ import annotations

from . import idle, jobs, watcher
from .routes import router
from .routes_model import router as model_router
from .routes_preview import device_open, device_router
from .routes_preview import router as preview_router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(model_router)
    ctx.register_router(preview_router)
    ctx.register_router(router)
    ctx.register_device_router(device_router, auth=device_open)   # Vorschau-Anmeldung ohne HydraHive-Login
    ctx.register_job("vibe-watcher", watcher.poll, watcher.INTERVAL_SECONDS)
    ctx.register_job("vibe-idle", idle.sweep, idle.SWEEP_SECONDS)
