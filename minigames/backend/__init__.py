"""Minigames-Modul — Backend.

register(ctx) →
  - Score-Router (/api/modules/minigames/scores[...]) — Highscores pro User
    + globale Bestenliste (Top-Score je User je Spiel)
  - Migrationen (scores-Tabelle, additiv)

Reines Spiel-Modul: die Spiele selbst laufen im Frontend (Canvas). Das Backend
speichert nur Scores und liefert die Bestenliste.
"""
from __future__ import annotations

from .score_routes import router as score_router


def register(ctx) -> None:
    ctx.register_router(score_router)
    ctx.register_migrations("migrations")
