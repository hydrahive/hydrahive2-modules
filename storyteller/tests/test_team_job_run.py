"""T1e: Lauf eines Team-Auftrags – eigene Sitzung, Runner durchlaufen, Status/Kosten setzen, Abbruch, Zeitgrenze."""
from __future__ import annotations

import asyncio

import pytest
from backend import storage, team_job_run, team_jobs
from conftest import PROJECT_ID

FIELDS = {"job": "check_scene", "role": "plausibility", "agent_name": "T — Plausibilität", "place_id": "s1",
          "place_title": "Am Hafen", "estimate_micros": 1, "user": "testuser"}


@pytest.fixture
def helper(setup_test_env):
    from hydrahive.agents import config as ac
    a = ac.create(agent_type="specialist", name="T — Plausibilität", llm_model="claude-sonnet-4-6", tools=[],
                  owner="testuser", temperature=0.7, max_tokens=1000, thinking_budget=0, project_id=PROJECT_ID)
    yield a
    ac.delete(a["id"])


def _job(helper):
    bid = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel"})["id"]
    return bid, team_jobs.create(PROJECT_ID, bid, {**FIELDS, "agent_id": helper["id"]})


def _fake(events, *, delay: float = 0.0, seen: list | None = None):
    async def run(session_id, user_input, **kw):
        if seen is not None:
            seen.append((session_id, user_input, kw))
        for ev in events:
            if delay:
                await asyncio.sleep(delay)
            yield ev
    return run


def _run(bid, job, **kw):
    return asyncio.run(team_job_run.execute(PROJECT_ID, bid, job["id"], task="Prüfe.", **kw))


def test_done_sets_status_session_summary_tokens_and_cost(helper, monkeypatch):
    from hydrahive.runner.events import Done, TextBlock, TextDelta
    seen: list = []
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake(
        [TextDelta(text="Zwei "), TextDelta(text="Befunde."), TextBlock(text="Zwei Befunde."),
         Done(message_id="m", iterations=2, input_tokens=1000, output_tokens=200, cache_read_tokens=50)], seen=seen))
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "done" and out["summary"] == "Zwei Befunde."
    assert out["tokens_in"] == 1050 and out["tokens_out"] == 200
    assert out["cost_micros"] is not None and out["cost_micros"] > 0
    session_id, text, _kw = seen[0]
    assert out["session_id"] == session_id and text == "Prüfe."
    from hydrahive.db import sessions as sdb
    s = sdb.get(session_id)
    assert s.agent_id == helper["id"] and s.user_id == "testuser" and s.project_id == PROJECT_ID
    assert s.metadata["storyteller_job"] == job["id"] and s.metadata["embedded_in"] == "storyteller"
    assert s.title.startswith("Storyteller-Auftrag: Szene prüfen")


def test_session_is_guarded_against_a_second_run(helper, monkeypatch):
    """Während der Helfer läuft, darf niemand über den Chat einen zweiten Lauf auf derselben Sitzung starten."""
    from hydrahive.runner import concurrency
    from hydrahive.runner.events import Done
    states: list = []

    async def run(session_id, user_input, **kw):
        states.append(concurrency.is_running(session_id))
        yield Done(message_id="m", iterations=1)
    monkeypatch.setattr(team_job_run, "_runner", lambda: run)
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert states == [True] and not concurrency.is_running(out["session_id"])


def test_error_event_sets_error(helper, monkeypatch):
    from hydrahive.runner.events import Error
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake([Error(message="LLM-Call fehlgeschlagen: 529")]))
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "error" and "529" in out["error"]


def test_runner_exception_sets_error_and_never_leaves_running(helper, monkeypatch):
    async def boom(session_id, user_input, **kw):
        raise RuntimeError("kaputt")
        yield  # pragma: no cover
    monkeypatch.setattr(team_job_run, "_runner", lambda: boom)
    bid, job = _job(helper)
    _run(bid, job)
    assert team_jobs.get(PROJECT_ID, bid, job["id"])["status"] == "error"


def test_timeout_sets_error(helper, monkeypatch):
    from hydrahive.runner.events import Done
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake([Done(message_id="m", iterations=1)], delay=1.0))
    monkeypatch.setattr(team_job_run, "TIMEOUT_SECONDS", 0.05)
    bid, job = _job(helper)
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert out["status"] == "error" and "Zeit" in out["error"]


def test_cancel_before_start_never_runs(helper, monkeypatch):
    seen: list = []
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake([], seen=seen))
    bid, job = _job(helper)
    team_jobs.request_cancel(PROJECT_ID, bid, job["id"])
    _run(bid, job)
    assert seen == [] and team_jobs.get(PROJECT_ID, bid, job["id"])["status"] == "cancelled"


def test_cancel_while_running_stops_the_task(helper, monkeypatch):
    from hydrahive.runner.events import Done
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake([Done(message_id="m", iterations=1)], delay=5.0))
    bid, job = _job(helper)

    async def scenario():
        task = team_job_run.start(PROJECT_ID, bid, job["id"], task="Prüfe.")
        await asyncio.sleep(0.05)
        assert team_job_run.cancel(PROJECT_ID, bid, job["id"]) is True
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
        assert task.cancelled()
    asyncio.run(scenario())
    assert team_jobs.get(PROJECT_ID, bid, job["id"])["status"] == "cancelled"


def test_helper_gone_is_an_error(helper, monkeypatch):
    from hydrahive.agents import config as ac
    seen: list = []
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake([], seen=seen))
    bid, job = _job(helper)
    ac.delete(helper["id"])
    _run(bid, job)
    out = team_jobs.get(PROJECT_ID, bid, job["id"])
    assert seen == [] and out["status"] == "error" and out["session_id"] == ""


def test_live_ids_only_while_task_runs(helper, monkeypatch):
    from hydrahive.runner.events import Done
    monkeypatch.setattr(team_job_run, "_runner", lambda: _fake([Done(message_id="m", iterations=1)], delay=0.2))
    bid, job = _job(helper)

    async def scenario():
        task = team_job_run.start(PROJECT_ID, bid, job["id"], task="Prüfe.")
        await asyncio.sleep(0.01)
        during = team_job_run.live_ids()
        await task
        return during, team_job_run.live_ids()
    during, after = asyncio.run(scenario())
    assert job["id"] in during and job["id"] not in after
