"""Ideen-Modul (Modul-ID scratchpad): einzelne Ideen je Nutzer statt eines Freitexts.

register(ctx) →
  - Router      /api/modules/scratchpad (meta, ideas, Anmerkungen, Task und Board zur Idee)
  - Migrationen module_scratchpad_ideas, module_scratchpad_idea_notes
  - Werkzeuge   idea_list, idea_read, idea_write
                read_scratchpad bleibt als veralteter Lese-Alias für ältere Agenten

Der Agent ändert den Text des Nutzers nie, er schreibt Anmerkungen daneben.
Die alten Dateien (user.md, agent.md) werden beim ersten Zugriff übernommen.
"""
from __future__ import annotations

from .routes import router
from .tools_read import LEGACY_READ_TOOL, LIST_TOOL, READ_TOOL
from .tools_write import WRITE_TOOL


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    ctx.register_tool(LIST_TOOL)
    ctx.register_tool(READ_TOOL)
    ctx.register_tool(WRITE_TOOL)
    ctx.register_tool(LEGACY_READ_TOOL)
