"""Mediacenter-Modul — Newznab-Suche und später SABnzbd/Agenten-Tools."""
from __future__ import annotations

from .routes_search import router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(router)
