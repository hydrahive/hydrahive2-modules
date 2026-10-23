"""Mailbox-Modul – Backend, Etappen M1 + M2 + M1b (mailbox/SPEC.md, PLAN-M1.md, PLAN-M2.md, PLAN-M1b.md).

register(ctx) →
  - Router    /api/modules/mailbox/…
  - Job       sync (Konten abgleichen, Archiv füllen)
  - Job       idle (IMAP IDLE je Konto – neue Mails sofort)
  - Migrationen 001–003 (Kern-DB: Konten, Abgleich-Status, Versandzählung, Einstellungen wie die Microsoft-App);
    Nachrichten im eigenen Index (index_db)
"""
from __future__ import annotations

from . import idle_manager, sync_job
from .routes import router

SYNC_SECONDS = 300
IDLE_CHECK_SECONDS = 60


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_job("sync", sync_job.job, interval_seconds=SYNC_SECONDS, initial_delay_seconds=60)
    # IDLE-Threads (daemon) passend zu den Konten halten; neue Mail → Abgleich sofort statt nach 5 Minuten
    ctx.register_job("idle", idle_manager.job, interval_seconds=IDLE_CHECK_SECONDS, initial_delay_seconds=90)
    ctx.register_migrations("migrations")
