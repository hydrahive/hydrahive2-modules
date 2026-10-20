"""Recht-Modul (legal) – Backend, Etappe L1 (legal/SPEC-LEGAL.md, PLAN-L1.md).

register(ctx) →
  - Router    /api/modules/legal/{laws, laws/{key}, norm, search, sync}
  - Werkzeuge legal_search, legal_norm (Gesetze sind öffentlich → Stufe normal)
  - Job       corpus_sync (stündlich geprüft, Abgleich wenn letzter Lauf > 20 h; erster Lauf 120 s nach Start)
  - Migration 001_corpus.sql
"""
from __future__ import annotations

from . import corpus_sync
from .routes import router
from .tools import TOOLS


def register(ctx) -> None:
    ctx.register_router(router)
    for tool in TOOLS:
        ctx.register_tool(tool)
    ctx.register_job("corpus_sync", corpus_sync.job, interval_seconds=3600, initial_delay_seconds=120)
    ctx.register_migrations("migrations")
