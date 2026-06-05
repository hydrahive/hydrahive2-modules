"""Archiver-Modul: USB-Festplatten in Projekt-Workspaces spiegeln.

register(ctx) -> Router (/api/modules/archiver/...) + Migrationen.
"""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
