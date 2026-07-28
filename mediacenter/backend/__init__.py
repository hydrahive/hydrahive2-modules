"""Mediacenter-Modul — Newznab-Suche und später SABnzbd/Agenten-Tools."""
from __future__ import annotations

from . import tools_actions, tools_read
from .routes_jobs import router as jobs_router
from .routes_search import router as search_router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(search_router)
    ctx.register_router(jobs_router)
    ctx.register_tool(tools_read.SEARCH_TOOL)
    ctx.register_tool(tools_actions.ENQUEUE_TOOL)
    ctx.register_tool(tools_actions.ENQUEUE_BATCH_TOOL)
    ctx.register_tool(tools_read.QUEUE_TOOL)
    ctx.register_tool(tools_read.HISTORY_TOOL)
