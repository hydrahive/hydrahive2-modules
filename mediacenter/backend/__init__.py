"""Mediacenter-Modul — Newznab-Suche und später SABnzbd/Agenten-Tools."""
from __future__ import annotations

from .routes_jobs import router as jobs_router
from .routes_search import router as search_router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(search_router)
    ctx.register_router(jobs_router)
