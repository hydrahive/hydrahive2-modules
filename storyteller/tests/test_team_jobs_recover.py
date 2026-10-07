"""T1e: Nach einem Neustart hängen keine Team-Aufträge auf „läuft …“ (Job alle 5 min, erster Lauf sofort)."""
from __future__ import annotations

import asyncio

import pytest

from backend import storage, team_job_run, team_jobs


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from hydrahive.tools import REGISTRY

    from backend.agent_tools import TOOLS
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def book_project():
    from hydrahive.projects import config as pc

    from backend.team import setup
    out = setup.create_book_project("testuser", {"title": "T", "kind": "novel", "language": "de"}, model="m")
    yield out["project_id"], out["book"]["id"]
    pc.delete(out["project_id"])


def _job(pid, bid, agent="a1"):
    return team_jobs.create(pid, bid, {"job": "check_scene", "role": "plausibility", "agent_id": agent,
                                       "place_id": "s", "user": "testuser"})


def test_recover_marks_dead_jobs_of_book_projects(book_project):
    pid, bid = book_project
    j = _job(pid, bid)
    n = asyncio.run(team_job_run.recover_stale_jobs())
    assert n == 1
    out = team_jobs.get(pid, bid, j["id"])
    assert out["status"] == "error" and out["error"] == team_jobs.RESTART_ERROR


def test_recover_keeps_live_jobs(book_project, monkeypatch):
    pid, bid = book_project
    j = _job(pid, bid)
    monkeypatch.setattr(team_job_run, "live_ids", lambda: {j["id"]})
    assert asyncio.run(team_job_run.recover_stale_jobs()) == 0
    assert team_jobs.get(pid, bid, j["id"])["status"] == "queued"


def test_recover_ignores_projects_without_books_and_never_creates_folders(book_project):
    from hydrahive.projects import config as pc
    from hydrahive.projects._paths import workspace_path
    plain = pc.create(name="ohne Buch", llm_model="m", created_by="testuser", members=["testuser"])
    try:
        ws = workspace_path(plain["id"])
        existed = (ws / "storyteller").exists()
        asyncio.run(team_job_run.recover_stale_jobs())
        assert (ws / "storyteller").exists() == existed
    finally:
        pc.delete(plain["id"])


def test_recover_survives_a_broken_book(book_project, monkeypatch):
    pid, bid = book_project
    j = _job(pid, bid)
    real = team_jobs.mark_stale
    calls = []

    def flaky(project_id, book_id, **kw):
        calls.append(book_id)
        if len(calls) == 1:
            raise OSError("Platte voll")
        return real(project_id, book_id, **kw)
    other = storage.create_book(pid, {"title": "Zweites", "kind": "novel"})["id"]
    k = _job(pid, other, agent="a2")
    monkeypatch.setattr(team_jobs, "mark_stale", flaky)
    n = asyncio.run(team_job_run.recover_stale_jobs())
    assert len(calls) == 2 and n == 1                 # ein Buch kaputt, das andere trotzdem bereinigt
    first_failed = calls[0]
    states = {bid: team_jobs.get(pid, bid, j["id"])["status"], other: team_jobs.get(pid, other, k["id"])["status"]}
    assert states[first_failed] == "queued"
    assert states[({bid, other} - {first_failed}).pop()] == "error"


def test_register_schedules_the_recovery_job():
    import backend as mod
    jobs = []

    class Ctx:
        def register_router(self, r): pass
        def register_migrations(self, d): pass
        def register_tool(self, t): pass
        def register_job(self, name, fn, **kw): jobs.append((name, fn, kw))
    mod.register(Ctx())
    names = {n: (fn, kw) for n, fn, kw in jobs}
    assert "recover_stale_team_jobs" in names
    fn, kw = names["recover_stale_team_jobs"]
    assert fn is team_job_run.recover_stale_jobs and kw.get("initial_delay_seconds") == 0
