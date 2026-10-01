"""Deep-Research-Modul Backend.

register(ctx) →
  - Router    /api/modules/deepresearch/runs*
  - Tool      research_report
  - Migration 001_deepresearch.sql
  - Startup-Job zur Bereinigung abgebrochener Läufe
"""
from __future__ import annotations

from . import recovery
from .routes import router
from .tools import research_run


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_tool(research_run.TOOL)
    ctx.register_migrations("migrations")
    ctx.register_job(
        "recover_stale_runs",
        recovery.recover_stale_runs,
        interval_seconds=300,
        initial_delay_seconds=0,
    )
