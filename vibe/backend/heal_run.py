"""Der Agentenlauf des Fehlerbehebens (PLAN-V1.md Baustein 6) – gleiche Sitzung wie der Chat, damit der Nutzer sieht,
was geschieht. Muster: Storyteller `team_job_run._drive` und Kern `start_run_task`.

Kostengrenze: vor jeder weiteren Runde (`IterationStart`) wird der Verbrauch DIESES Laufs (Summe `llm_calls` der
Sitzung minus Stand vor dem Lauf) + Verbrauch der letzten Runde mit der Grenze verglichen; drüber → Ende zwischen
zwei Runden, nie mitten im Modellaufruf. Dieser Teil ist nur gegen den echten Kern prüfbar (Probe auf hydratest).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10 * 60


def _n(v) -> int:
    return int(v or 0)


def usage(session_id: str) -> tuple[int, int]:
    """(Summe aller Modellaufrufe der Sitzung, Verbrauch des letzten Aufrufs) in Tokens inkl. Cache."""
    from hydrahive.db import llm_calls
    total = last = 0
    for r in llm_calls.for_session(session_id):
        last = _n(r["prompt_tokens"]) + _n(r["cache_read_tokens"]) + _n(r["cache_creation_tokens"]) + _n(r["completion_tokens"])
        total += last
    return total, last


async def drive(project_id: str, session_id: str, task: str, *, limit_tokens: int) -> dict:
    import asyncio

    from hydrahive.api._session_broadcast import broadcaster
    from hydrahive.api.routes._sse import encode_event
    from hydrahive.runner import run as runner_run
    from hydrahive.runner.concurrency import session_run_guard
    from hydrahive.runner.event_bus import bus
    from hydrahive.runner.events import Done, IterationStart

    before, _ = usage(session_id)
    limited = False
    done = None
    bus.open(session_id)
    try:
        async with session_run_guard(session_id):
            broadcaster.broadcast(session_id, '{"t":"start"}')
            gen = runner_run(session_id, task)
            try:
                async def _loop() -> None:
                    nonlocal limited, done
                    async for ev in gen:
                        if isinstance(ev, IterationStart):
                            total, last = usage(session_id)
                            if limit_tokens and (total - before) + last > limit_tokens:
                                limited = True
                                return
                        if isinstance(ev, Done):
                            done = ev
                        bus.publish(session_id, encode_event(ev))
                await asyncio.wait_for(_loop(), timeout=TIMEOUT_SECONDS)
            finally:
                await gen.aclose()
    finally:
        bus.close(session_id)
        broadcaster.broadcast(session_id, '{"t":"done"}')
    total, _ = usage(session_id)
    return {"tokens": max(0, total - before), "limited": limited, "done": done is not None}
