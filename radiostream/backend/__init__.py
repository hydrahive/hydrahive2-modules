"""Modul Radiostream – eigenes Webradio (Spec radiostream/SPEC.md).

Etappe 1: Bibliothek von der NAS-Freigabe einlesen (nur lesen), durchsuchen, vorhören.
Etappe 2 (PLAN-E2.md): Sendebetrieb (Icecast + Liquidsoap), AutoDJ, Hörer-Seite auf eigenem Port.
register(ctx) → Router /api/modules/radiostream (Bibliothek, Zuspielung, Sender), Migrationen, Job „nächtliches Einlesen“.
"""
from __future__ import annotations

from . import feed, nightly, station_routes
from .routes import router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(router)
    ctx.register_router(feed.router)
    ctx.register_router(station_routes.router)
    ctx.register_job("radiostream-nightly-scan", nightly.tick, interval_seconds=3600, initial_delay_seconds=120)
