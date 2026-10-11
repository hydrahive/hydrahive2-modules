"""Tonstudio — Songs mit KI erzeugen, arrangieren, mischen (SPEC.md).

M1: Songs (Format hydrahive.song v1, Versionen, Papierkorb), Bibliothek (eigene Clips + Projekt-Audio + Upload),
Clips erzeugen über austauschbare Anbieter (providers/, erster Adapter: Lyria über OpenRouter).
"""
from __future__ import annotations

from .routes import router

__all__ = ["register", "router"]


def register(ctx) -> None:
    ctx.register_router(router)
