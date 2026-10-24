"""Mailbox-Modul – Backend (mailbox/SPEC.md, PLAN-*.md).

register(ctx) →
  - Router    /api/modules/mailbox/…
  - Job       sync (Konten abgleichen, Archiv füllen)
  - Job       idle (IMAP IDLE je Konto – neue Mails sofort)
  - Job       tool_sync (Mailbox-Werkzeuge am Projekt-Agenten passend zu den Freigaben)
  - Werkzeuge mailbox_* für Agenten (nur freigegebene Konten)
  - Migrationen 001–003 (Kern-DB: Konten, Abgleich-Status, Versandzählung, Einstellungen wie die Microsoft-App);
    Nachrichten im eigenen Index (index_db)
"""
from __future__ import annotations

from . import agent_tool_sync, idle_manager, sync_job
from .agent_tools import TOOLS
from .routes import router

SYNC_SECONDS = 300
IDLE_CHECK_SECONDS = 60


def register(ctx) -> None:
    ctx.register_router(router)
    for tool in TOOLS:                       # M3a: Lese-Werkzeuge, nur für freigegebene Konten
        ctx.register_tool(tool)
    ctx.register_job("sync", sync_job.job, interval_seconds=SYNC_SECONDS, initial_delay_seconds=60)
    # IDLE-Threads (daemon) passend zu den Konten halten; neue Mail → Abgleich sofort statt nach 5 Minuten
    ctx.register_job("idle", idle_manager.job, interval_seconds=IDLE_CHECK_SECONDS, initial_delay_seconds=90)
    ctx.register_migrations("migrations")
    # Freigaben aus 0.6/0.7.0: Werkzeuge am Projekt-Agenten nachtragen (einmal kurz nach dem Start)
    ctx.register_job("tool_sync", _tool_sync_once, interval_seconds=86400, initial_delay_seconds=30)


async def _tool_sync_once() -> None:
    import asyncio
    await asyncio.to_thread(agent_tool_sync.sync_all)
