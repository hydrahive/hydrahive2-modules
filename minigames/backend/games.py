"""Bekannte Spiele (Server-Whitelist) + Score-Grenzen.

Verhindert, dass beliebige game_ids oder absurde Scores in den Store geschrieben
werden. Beim Hinzufügen eines neuen Spiels hier ergänzen (analog zur Frontend-
Registry). Kein echtes Anti-Cheat — nur Plausibilität für ein privates System.
"""
from __future__ import annotations

# game_id → maximal plausibler Score (Müll-Schutz)
GAMES: dict[str, int] = {
    "snake": 100_000,
    "invaders": 500_000,
    "frogger": 200_000,
}


def is_valid_game(game_id: str) -> bool:
    return game_id in GAMES


def is_plausible_score(game_id: str, score: int) -> bool:
    if not isinstance(score, int) or score < 0:
        return False
    return score <= GAMES.get(game_id, 0)
