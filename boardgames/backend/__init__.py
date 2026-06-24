"""Brettspiele-Modul — Backend.

register(ctx) →
  - Ergebnis-Router (/api/modules/boardgames/results[...]) — W/L/Remis pro User
    + globale Bestenliste (meiste Siege je User je Spiel)
  - Migrationen (results-Tabelle, additiv)

Die Spiele selbst (Engine, KI, Brett) laufen im Frontend. Das Backend speichert
nur Partie-Ergebnisse. (LLM-Gegner folgt in Runde 2 als eigener Router.)
"""
from __future__ import annotations

from .result_routes import router as result_router


def register(ctx) -> None:
    ctx.register_router(result_router)
    ctx.register_migrations("migrations")
