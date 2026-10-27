"""Modul Radiostream – eigenes Webradio (Spec radiostream/SPEC.md).

Etappe 1: Bibliothek von der NAS-Freigabe einlesen (nur lesen), durchsuchen, vorhören.
register(ctx) → Router /api/modules/radiostream, Migration 001_library.sql, Job „nächtliches Einlesen“.
"""
from __future__ import annotations

from . import nightly
from .routes import router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(router)
    ctx.register_job("radiostream-nightly-scan", nightly.tick, interval_seconds=3600, initial_delay_seconds=120)
