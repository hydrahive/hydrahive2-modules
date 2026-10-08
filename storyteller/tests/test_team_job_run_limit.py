"""A1: Kostengrenze während eines Team-Auftrags (Spec kostengrenze.md §4) und Kosten bei jedem Endzustand.

Der Kern schreibt je Modellaufruf eine Zeile in ``llm_calls``. Vor jeder weiteren Runde (``IterationStart`` ab 2):
verbraucht + Verbrauch der letzten Runde > Grenze → Lauf zwischen zwei Runden beenden, Status „limit“.
"""
from __future__ import annotations

import asyncio

import pytest
from conftest import PROJECT_ID

from backend import storage, team_job_run, team_jobs

FIELDS = {"job": "check_scene", "role": "plausibility", "agent_name": "T — Plausibilität", "place_id": "s1",
          "place_title": "Am Hafen", "estimate_micros": 1, "user": "testuser"}


@pytest.fixture
def helper(setup_test_env):
    from hydrahive.agents import config as ac
    a = ac.create(agent_type="specialist", name="T — Plausibilität", llm_model="claude-sonnet-4-6", tools=[],
                  owner="testuser", temperature=0.7, max_tokens=1000, thinking_budget=0, project_id=PROJECT_ID)
    yield a
    ac.delete(a["id"])


def _job(helper, limit=0):
    bid = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel"})["id"]
    return bid, team_jobs.create(PROJECT_ID, bid, {**FIELDS, "agent_id": helper["id"], "limit_tokens": limit})


def _call(session_id, *, prompt=3000, out=500, cache=0, cost=10):
    from hydrahive.db import llm_calls
    llm_calls.insert(llm_calls.LlmCall(
        session_id=session_id, agent_id=None, user_id="testuser", provider="anthropic", model="claude-sonnet-4-6",
        temperature=0.7, max_tokens=1000, reasoning_effort=None, prompt_tokens=prompt, completion_tokens=out,
        cache_read_tokens=cache, cache_creation_tokens=0, stop_reason="tool_use", ttft_ms=None, total_ms=1,
        cost_micros=cost, turn_in_session=1))


def _rounds(n, *, tail=(), seen=None, **call):
    """Fake-Runner wie der Kern: je Runde IterationStart, dann Modellaufruf (llm_calls-Zeile), dann Text."""
    from hydrahive.runner.events import Done, IterationStart, MessageStart, TextDelta

    async def run(session_id, user_input, **kw):
        try:
            for i in range(1, n + 1):
                yield IterationStart(iteration=i)
                _call(session_id, **call)
                if seen is not None:
                    seen.append(i)
                yield MessageStart()
                yield TextDelta(text=f"Runde {i}.")
            for ev in tail:
                yield ev
            yield Done(message_id="m", iterations=n, input_tokens=n * 3000, output_tokens=n * 500)
        finally:
            if seen is not None:
                seen.append("closed")
    return run


def _run(bid, job):
    return asyncio.run(team_job_run.execute(PROJECT_ID, bid, job["id"], task="Prüfe."))


def test_limit_stops_between_rounds_and_keeps_usage(helper, monkeypatch):
    """Je Runde 3000 + 500. Grenze 8000: vor Runde 2 (3500 + 3500 = 7000) weiter, vor Runde 3 (7000 + 3500) Ende."""
    seen: list = []
    monkeypatch.setattr(team_job_run, "_runner", lambda: _rounds(5, seen=seen))
    bid, job = _job(helper, limit=8000)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "limit" and out["finished_at"]
    assert seen == [1, 2, "closed"]                       # Runde 3 nie gestartet, Runner sauber geschlossen
    assert out["tokens_in"] == 6000 and out["tokens_out"] == 1000 and out["cost_micros"] == 20
    assert out["summary"] == "Runde 2."


def test_cache_tokens_count_towards_the_limit(helper, monkeypatch):
    """Eingabe = prompt + Cache (wie bei „done“). 1000 + 2500 Cache + 500 = 4000 je Runde; Grenze 7000 → Ende vor 2."""
    monkeypatch.setattr(team_job_run, "_runner", lambda: _rounds(3, prompt=1000, cache=2500))
    bid, job = _job(helper, limit=7000)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "limit" and out["tokens_in"] == 3500 and out["tokens_out"] == 500


def test_exactly_at_limit_continues(helper, monkeypatch):
    """Grenze 7000: vor Runde 2 genau 3500 + 3500 = 7000 → weiter; vor Runde 3 Ende."""
    seen: list = []
    monkeypatch.setattr(team_job_run, "_runner", lambda: _rounds(3, seen=seen))
    bid, job = _job(helper, limit=7000)
    _run(bid, job)
    assert team_jobs.get(PROJECT_ID, bid, job["id"])["status"] == "limit" and 2 in seen and 3 not in seen


def test_without_limit_runs_to_the_end(helper, monkeypatch):
    seen: list = []
    monkeypatch.setattr(team_job_run, "_runner", lambda: _rounds(5, seen=seen))
    bid, job = _job(helper, limit=0)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "done" and seen[:5] == [1, 2, 3, 4, 5]


def test_limit_stop_ends_the_helper_session_activity(helper, monkeypatch):
    from hydrahive.runner import activity
    stopped: list = []
    monkeypatch.setattr(activity, "stop", lambda sid: stopped.append(sid))
    monkeypatch.setattr(team_job_run, "_runner", lambda: _rounds(5))
    bid, job = _job(helper, limit=8000)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "limit" and out["session_id"] in stopped


def test_limit_stop_marks_core_session_abandoned_but_done_stays_completed(helper, monkeypatch):
    """Der Kern führt je Agent eine Sitzungsdatei (session_start/session_end). An der Grenze: „abandoned“.
    Ein normal beendeter Lauf (Kern setzt „completed“) wird nicht überschrieben."""
    from hydrahive.runner.events import Done, IterationStart
    from hydrahive.tools._sessions import session_end, session_get, session_start

    def runner(n, finish):
        async def run(session_id, user_input, **kw):
            session_start(helper["id"], session_id)
            for i in range(1, n + 1):
                yield IterationStart(iteration=i)
                _call(session_id)
            if finish:
                session_end(helper["id"], session_id, status="completed")
                yield Done(message_id="m", iterations=n)
        return run
    monkeypatch.setattr(team_job_run, "_runner", lambda: runner(5, False))
    bid, job = _job(helper, limit=8000)
    _run(bid, job)
    sid = team_jobs.get(PROJECT_ID, bid, job["id"])["session_id"]
    assert session_get(helper["id"], sid)["status"] == "abandoned"
    monkeypatch.setattr(team_job_run, "_runner", lambda: runner(1, True))
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "done" and session_get(helper["id"], out["session_id"])["status"] == "completed"


def test_error_keeps_usage(helper, monkeypatch):
    from hydrahive.runner.events import Error
    monkeypatch.setattr(team_job_run, "_runner", lambda: _rounds(2, tail=[Error(message="LLM-Call fehlgeschlagen")]))
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "error" and out["tokens_in"] == 6000 and out["tokens_out"] == 1000 and out["cost_micros"] == 20


def test_timeout_keeps_usage(helper, monkeypatch):
    from hydrahive.runner.events import IterationStart

    async def slow(session_id, user_input, **kw):
        yield IterationStart(iteration=1)
        _call(session_id)
        await asyncio.sleep(1.0)
        yield IterationStart(iteration=2)
    monkeypatch.setattr(team_job_run, "_runner", lambda: slow)
    monkeypatch.setattr(team_job_run, "TIMEOUT_SECONDS", 0.1)
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "error" and "Zeit" in out["error"] and out["tokens_in"] == 3000 and out["cost_micros"] == 10


def test_cancel_keeps_usage(helper, monkeypatch):
    from hydrahive.runner.events import IterationStart
    reached = asyncio.Event()

    async def hang(session_id, user_input, **kw):
        yield IterationStart(iteration=1)
        _call(session_id)
        reached.set()
        await asyncio.sleep(10)
        yield IterationStart(iteration=2)
    monkeypatch.setattr(team_job_run, "_runner", lambda: hang)
    bid, job = _job(helper)

    async def main():
        task = team_job_run.start(PROJECT_ID, bid, job["id"], task="Prüfe.")
        await asyncio.wait_for(reached.wait(), 5)
        team_job_run.cancel(PROJECT_ID, bid, job["id"])
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(main())
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "cancelled" and out["tokens_in"] == 3000 and out["tokens_out"] == 500 and out["cost_micros"] == 10
