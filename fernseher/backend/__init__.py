"""Fernseher-Modul – Backend (SPEC.md).

register(ctx) → Router (/api/modules/fernseher/*), sechs Agenten-Werkzeuge (tv_*), Migration (Einstellungen).
Submodule als Modul importieren (nicht `from .tools import ALL`), damit `backend.tools` das Modul bleibt.
"""
from __future__ import annotations

from . import tools
from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    for tool in tools.ALL:
        ctx.register_tool(tool)
    ctx.register_migrations("migrations")
