"""Storyteller — KI-gestütztes Schreiben von Büchern.

Specs (lokal): storyteller/docs/specs/stufe-1-grundoberflaeche.md, stufe-1b-ablage-ki.md.
Stufe 1b: Bücher als Dateien im Projektordner (storage.py), Versionen gegen stilles
Überschreiben, Schnappschüsse als Dateien, KI-Vorschläge über die HydraHive-Modelle (ai.py).
"""
from __future__ import annotations

from .routes import router

__all__ = ["router", "register"]


def register(ctx) -> None:
    ctx.register_router(router)
