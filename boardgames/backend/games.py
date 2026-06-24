"""Bekannte Brettspiele (Server-Whitelist) + erlaubte Modi/Ergebnisse.

Beim Hinzufügen eines neuen Spiels hier ergänzen (analog zur Frontend-Registry).
"""
from __future__ import annotations

GAMES: set[str] = {"chess"}
MODES: set[str] = {"hotseat", "ai", "llm"}
RESULTS: set[str] = {"win", "loss", "draw"}


def is_valid_game(game_id: str) -> bool:
    return game_id in GAMES


def is_valid_mode(mode: str) -> bool:
    return mode in MODES


def is_valid_result(result: str) -> bool:
    return result in RESULTS
