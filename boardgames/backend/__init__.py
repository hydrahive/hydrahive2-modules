"""Brettspiele-Modul — Backend.

register(ctx) →
  - Ergebnis-Router (/api/modules/boardgames/results[...]) — W/L/Remis pro User
    + globale Bestenliste (meiste Siege je User je Spiel)
  - Schach-Router (/api/modules/boardgames/chess/llm-move) — LLM-Gegner: wählt
    einen Zug aus den vom Frontend gelieferten legalen Zügen (Engine = SSOT)
  - Migrationen (results-Tabelle, additiv)

Die Spiele selbst (Engine, KI, Brett) laufen im Frontend. Das Backend speichert
Ergebnisse und vermittelt den LLM-Zug (API-Key bleibt serverseitig).
"""
from __future__ import annotations

from .chess_routes import router as chess_router
from .result_routes import router as result_router


def register(ctx) -> None:
    ctx.register_router(result_router)
    ctx.register_router(chess_router)
    ctx.register_migrations("migrations")
