"""Storyteller — KI-gestütztes Schreiben von Büchern.

Specs (lokal): storyteller/docs/specs/stufe-1-grundoberflaeche.md, stufe-1b-ablage-ki.md.
Stufe 1b: Bücher als Dateien im Projektordner (storage.py), Versionen gegen stilles
Überschreiben, Schnappschüsse als Dateien, KI-Vorschläge über die HydraHive-Modelle (ai.py).
Ghostwriter (docs/specs/ghostwriter.md): Szene schreiben (ghost.py), Läufe im Hintergrund
(run_engine.py, Tabelle module_storyteller_runs), Gliederung aus Idee (outline.py), Interview (interviews.py),
Agent-Werkzeuge für den Chat (agent_tools/).
"""
from __future__ import annotations

from . import runs, team_job_run
from .agent_tools import TOOLS
from .routes import router

__all__ = ["router", "register"]


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
    # Ghostwriter-Läufe ohne lebenden Task (Dienst neu gestartet) als abgebrochen markieren.
    ctx.register_job("recover_stale_runs", runs.recover_stale_runs, interval_seconds=300, initial_delay_seconds=0)
    # Team-Aufträge (T1e) ebenso: nach einem Neustart kein ewiges „läuft …“.
    ctx.register_job("recover_stale_team_jobs", team_job_run.recover_stale_jobs, interval_seconds=300,
                     initial_delay_seconds=0)
    # Agent im Chat (G4): Bücher lesen, Szenentext als Vorschlag ablegen. Nie direkt ins Buch schreiben.
    for tool in TOOLS:
        ctx.register_tool(tool)
