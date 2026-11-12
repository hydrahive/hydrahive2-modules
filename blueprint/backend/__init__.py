"""Blueprint-Modul — Backend.

register(ctx) →
  - Router     (/api/modules/blueprint/boards) — per-User Board-CRUD, Projekt am Board,
               Vorschlag übernehmen/verwerfen, frühere Fassungen
  - Migrationen (Boards-Tabelle, Projekt und Vorschlag, Versionen; additiv)
  - Agent-Tool blueprint_read — eigene Boards auflisten und als Text lesen
  - Agent-Tool blueprint_propose — Entwurf als Vorschlag ablegen (überschreibt nie)

Blueprint ist ein visueller Node-Editor (xyflow) als nonverbaler Ideen-Kanal
User → Agent: Layouts + Funktionspläne auf einem Board, als graph_json gespeichert.
Der Agent liest Boards über blueprint_read (Task 9111b283). Über die REST-Route
kam er nicht heran (Login nötig, fetch_url sperrt interne Adressen).
"""
from __future__ import annotations

from .routes import router
from .tools import READ_TOOL
from .tools_propose import PROPOSE_TOOL


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    ctx.register_tool(READ_TOOL)
    ctx.register_tool(PROPOSE_TOOL)
