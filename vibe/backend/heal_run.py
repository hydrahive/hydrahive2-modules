"""Der Agentenlauf des Fehlerbehebens (PLAN-V1.md Baustein 6) – gleiche Sitzung wie der Chat, damit der Nutzer sieht,
was geschieht. Muster: Storyteller `team_job_run._drive` und Kern `start_run_task`.

Kostengrenze: vor jeder weiteren Runde (`IterationStart`) wird der Verbrauch DIESES Laufs (Summe `llm_calls` der
Sitzung, nur Zeilen nach Laufbeginn) + Verbrauch der letzten Runde mit der Grenze verglichen; drüber → Ende zwischen
zwei Runden, nie mitten im Modellaufruf. Dieser Teil ist nur gegen den echten Kern prüfbar (Probe auf hydratest).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10 * 60


def _n(v) -> int:
    return int(v or 0)


def _tokens(r) -> int:
    return _n(r["prompt_tokens"]) + _n(r["cache_read_tokens"]) + _n(r["cache_creation_tokens"]) + _n(r["completion_tokens"])


def spent(rows: list, before_n: int) -> int:
    """Tokens dieses Laufs: nur Modellaufrufe NACH den `before_n` Zeilen, die vor dem Lauf schon da waren."""
    return sum(_tokens(r) for r in rows[before_n:])


def over_limit(rows: list, before_n: int, limit: int) -> bool:
    """Vor einer weiteren Runde: bisheriger Verbrauch des Laufs + Größe der letzten Runde des LAUFS > Grenze.
    Gibt es im Lauf noch keine Runde, gibt es nichts zu schätzen → nie darüber. Die letzte Runde des Chats davor zählt
    nicht (an hydratest 5.11. gemessen: sonst Abbruch nach 0 Tokens bei langem Chat)."""
    mine = rows[before_n:]
    if not limit or not mine:
        return False
    return sum(_tokens(r) for r in mine) + _tokens(mine[-1]) > limit


def _rows(session_id: str) -> list:
    from hydrahive.db import llm_calls
    return llm_calls.for_session(session_id)


async def drive(project_id: str, session_id: str, task: str, *, limit_tokens: int) -> dict:
    import asyncio

    from hydrahive.api._session_broadcast import broadcaster
    from hydrahive.api.routes._sse import encode_event
    from hydrahive.runner import run as runner_run
    from hydrahive.runner.concurrency import session_run_guard
    from hydrahive.runner.event_bus import bus
    from hydrahive.runner.events import Done, IterationStart

    before_n = len(_rows(session_id))
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
                            if over_limit(_rows(session_id), before_n, limit_tokens):
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
    return {"tokens": spent(_rows(session_id), before_n), "limited": limited, "done": done is not None}
