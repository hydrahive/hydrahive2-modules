"""Storyteller — KI-gestütztes Schreiben von Büchern.

Specs (lokal): storyteller/docs/specs/stufe-1-grundoberflaeche.md, stufe-1b-ablage-ki.md.
Stufe 1b: Bücher als Dateien im Projektordner (storage.py), Versionen gegen stilles
Überschreiben, Schnappschüsse als Dateien, KI-Vorschläge über die HydraHive-Modelle (ai.py).
Ghostwriter (docs/specs/ghostwriter.md): Szene schreiben (ghost.py), Läufe im Hintergrund
(run_engine.py, Tabelle module_storyteller_runs), Gliederung aus Idee (outline.py).
"""
from __future__ import annotations

from . import runs
from .routes import router

__all__ = ["router", "register"]


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    # Ghostwriter-Läufe ohne lebenden Task (Dienst neu gestartet) als abgebrochen markieren.
    ctx.register_job("recover_stale_runs", runs.recover_stale_runs, interval_seconds=300, initial_delay_seconds=0)
