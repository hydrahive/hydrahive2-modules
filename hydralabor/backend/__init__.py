"""Modul Hydra-Labor – sicher an HydraHive mitbauen (SPEC.md, PLAN-L1.md).

L1: abgeschotteter Container mit eigenem Netz und Sperre, Labor-Projekt mit verwaltetem Labor-Agenten, Assistent,
Testlauf, Netz prüfen, Zurücksetzen, Entfernen. Nur Admins.
"""
from __future__ import annotations

import logging

from . import skill_sync, state
from .routes import router
from .routes_github import router as github_router
from .routes_probe import device_open, device_router
from .routes_probe import router as probe_router

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(github_router)          # zuerst: router hat /{action}, das würde /submit usw. fangen
    ctx.register_router(probe_router)
    ctx.register_router(router)
    ctx.register_device_router(device_router, auth=device_open)   # Probe-Anmeldung ohne HydraHive-Login
    skill_sync.install()
    try:
        state.recover_after_restart()
    except Exception:  # noqa: BLE001 - Tabelle evtl. noch nicht da (erste Installation); Modulstart nie verhindern
        logger.info("Hydra-Labor: Zustand beim Start nicht lesbar (erste Installation?)")
