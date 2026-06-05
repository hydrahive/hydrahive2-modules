"""Archiver-Modul: USB-Festplatten in Projekt-Workspaces spiegeln.

register(ctx) -> Router (/api/modules/archiver/...) + Migrationen.
"""
from __future__ import annotations

import logging

from .routes import router

logger = logging.getLogger(__name__)
logging.getLogger("hydrahive.modules.archiver").setLevel(logging.INFO)


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    _cleanup_stale_jobs()


def _cleanup_stale_jobs() -> None:
    """Jobs die beim letzten Restart noch 'running' waren → 'failed' markieren."""
    try:
        from hydrahive.db.connection import db
        with db() as c:
            n = c.execute(
                "UPDATE module_archiver_jobs SET status='failed' WHERE status='running'"
            ).rowcount
        if n:
            logger.info("archiver: %d verwaiste Jobs als 'failed' markiert", n)
    except Exception as exc:
        logger.warning("archiver: cleanup fehlgeschlagen: %s", exc)
