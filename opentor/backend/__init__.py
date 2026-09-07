"""OpenTor OSINT-Modul: kontrollierte read-only Tor-Recherche."""
from __future__ import annotations

from . import tools
from .routes import router


def register(ctx) -> None:
    ctx.register_migrations("migrations")
    ctx.register_router(router)
    ctx.register_tool(tools.STATUS_TOOL)
    ctx.register_tool(tools.SEARCH_TOOL)
    ctx.register_tool(tools.FETCH_TOOL)
    ctx.register_tool(tools.EXTRACT_TOOL)
