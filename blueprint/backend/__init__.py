"""Blueprint-Modul — Backend.

register(ctx) →
  - Router     (/api/modules/blueprint/boards) — per-User Board-CRUD
  - Migrationen (Boards-Tabelle, additiv)

Blueprint ist ein visueller Node-Editor (xyflow) als nonverbaler Ideen-Kanal
Till → Agent: Layouts + Funktionspläne auf einem Board, als graph_json gespeichert.
Kein Agent-Tool nötig — der Agent liest Boards über die REST-Route, wenn Till
im Chat darauf verweist.
"""
from __future__ import annotations

from .routes import router


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
