"""Zerlege-Werkstatt: autorisierte statische Untersuchung in isolierter Umgebung."""
from __future__ import annotations

from .routes import router
from .tools import ALL_TOOLS


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    for tool in ALL_TOOLS:
        ctx.register_tool(tool)
