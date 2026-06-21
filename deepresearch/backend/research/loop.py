"""Iterativer Research-Controller (IterResearch-Stil).

plan → pro Runde [queries → gather → synthesize → stop?] → finaler Bericht.
Emittiert reiche Fortschritts-Events (Phase, Runde, Quellen, aktuell gelesene Quelle)
für die Live-Such-Anzeige im Frontend.
"""
from __future__ import annotations

import logging
import time
from typing import Callable

from . import planner, queries, synthesize
from .gather import gather_round
from .models import RunState
from .report_writer import write_report

logger = logging.getLogger(__name__)

# emit(payload: dict) — schreibt den Fortschritt (z.B. in die DB-Zeile).
EmitFn = Callable[[dict], None] | None


def _make_emit(state: RunState, started: float, emit: EmitFn) -> Callable[..., None]:
    def _emit(phase: str, current: dict | None = None) -> None:
        if emit is None:
            return
        emit({
            "phase": phase,
            "round": state.round,
            "queries": len(state.queries_used),
            "total_sources": len(state.urls_seen),
            "total_findings": len(state.findings),
            "current": current,
            "category": state.category,
            "elapsed_s": round(time.monotonic() - started, 1),
        })
    return _emit


async def run_research(
    state: RunState,
    *,
    progress: EmitFn = None,
    max_rounds: int = 6,
    min_rounds: int = 2,
    max_time: float = 300.0,
) -> dict:
    """Führt den Lauf aus und gibt {markdown, sources, stats, category} zurück."""
    started = time.monotonic()
    emit = _make_emit(state, started, progress)

    emit("planning")
    await planner.make_plan(state)

    for rnd in range(1, max_rounds + 1):
        state.round = rnd
        qs = await queries.generate_queries(state, rnd == 1)
        emit("searching")
        if qs:
            await gather_round(state, qs, emit)
        emit("analyzing")
        await synthesize.synthesize(state)

        if rnd >= min_rounds and time.monotonic() - started < max_time:
            if await synthesize.should_stop(state):
                break
        if time.monotonic() - started >= max_time:
            logger.info("deepresearch: Zeitbudget erreicht nach Runde %s", rnd)
            break

    emit("writing")
    markdown = await write_report(state)

    stats = {
        "rounds": state.round,
        "queries": len(state.queries_used),
        "urls": len(state.urls_seen),
        "sources": len(state.sources()),
        "duration_s": round(time.monotonic() - started, 1),
        "model": state.model or "default",
    }
    emit("done")
    return {
        "markdown": markdown,
        "sources": state.sources(),
        "stats": stats,
        "category": state.category,
    }
