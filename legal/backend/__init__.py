"""Recht-Modul (legal) – Backend, Etappe L1 (legal/SPEC-LEGAL.md, PLAN-L1.md).

register(ctx) →
  - Router    /api/modules/legal/{laws, laws/{key}, norm, search, sync}
  - Werkzeuge legal_search, legal_norm (Gesetze sind öffentlich → Stufe normal)
  - Job       corpus_sync (stündlich geprüft, Abgleich wenn letzter Lauf > 20 h; erster Lauf 120 s nach Start)
  - Job       orphans (täglich: Fälle ohne Projekt markieren, nach 30 Tagen sichern + löschen)
  - Migrationen 001_corpus.sql, 002_cases.sql
L2 (PLAN-L2.md): Fälle = Projekte mit Rechts-Agent, Fallakte, Fristenrechner, Fall-Werkzeuge (privat).
L3 (PLAN-L3.md): Schriftverkehr, Brief-Vorlagen + Prüfliste, Brief-Werkzeuge, Skill rechtsbrief (System-Skill).
"""
from __future__ import annotations

from . import corpus_sync, orphans, skill_sync
from .routes import router
from .tools import TOOLS


def register(ctx) -> None:
    ctx.register_router(router)
    for tool in TOOLS:
        ctx.register_tool(tool)
    ctx.register_job("corpus_sync", corpus_sync.job, interval_seconds=3600, initial_delay_seconds=120)
    ctx.register_job("orphans", orphans.job, interval_seconds=86400, initial_delay_seconds=600)
    ctx.register_migrations("migrations")
    skill_sync.install()
