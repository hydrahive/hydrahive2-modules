"""Mailbox-Modul – Backend, Etappe M1 (mailbox/SPEC.md, PLAN-M1.md).

register(ctx) →
  - Router    /api/modules/mailbox/…
  - Job       sync (Konten abgleichen, Archiv füllen)
  - Migrationen 001_mailbox.sql (Kern-DB: Konten, Abgleich-Status); Nachrichten im eigenen Index (index_db)
"""
from __future__ import annotations

from . import sync_job
from .routes import router

SYNC_SECONDS = 300


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_job("sync", sync_job.job, interval_seconds=SYNC_SECONDS, initial_delay_seconds=60)
    ctx.register_migrations("migrations")
