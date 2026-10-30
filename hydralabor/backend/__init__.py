"""Modul Hydra-Labor – sicher an HydraHive mitbauen (SPEC.md, PLAN-L1.md).

L1: abgeschotteter Container mit eigenem Netz und Sperre, Labor-Projekt mit verwaltetem Labor-Agenten, Assistent,
Testlauf, Netz prüfen, Zurücksetzen, Entfernen. Nur Admins.
"""
from __future__ import annotations

from . import skill_sync, state
from .routes import router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(router)
    skill_sync.install()
    try:
        state.recover_after_restart()
    except Exception:  # noqa: BLE001 - Tabelle evtl. noch nicht da (erste Installation); Modulstart nie verhindern
        pass
