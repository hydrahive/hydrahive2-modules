"""Scratchpad-Modul: per-User Notizzettel (Mensch- + Agent-Zone) + Agent-Tools.

register(ctx) -> API-Router (/api/modules/scratchpad) + read/write_scratchpad-Tools.
Keine Migration (dateibasiert: data_dir/scratchpad/<user>/{user,agent}.md).
"""
from __future__ import annotations

from .routes import router
from .tools import READ_TOOL, WRITE_TOOL


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_tool(READ_TOOL)
    ctx.register_tool(WRITE_TOOL)
