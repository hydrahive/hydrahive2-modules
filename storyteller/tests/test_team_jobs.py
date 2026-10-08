"""T1e: Ablage der Team-Aufträge (Datei je Auftrag, Status nur vorwärts, Grenzen)."""
from __future__ import annotations

import threading

import pytest
from backend import storage, team_jobs
from backend._files import StoryError
from conftest import PROJECT_ID

FIELDS = {"job": "check_scene", "role": "plausibility", "agent_id": "a1", "agent_name": "T — Plausibilität",
          "place_id": "s1", "place_title": "Am Hafen", "estimate_micros": 1200, "user": "testuser"}


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel"})
    return b["id"]


def _new(bid, **kw):
    return team_jobs.create(PROJECT_ID, bid, {**FIELDS, **kw})


def test_create_lists_newest_first_and_starts_queued():
    bid = _book()
    a = _new(bid)
    b = _new(bid, role="editor", job="edit_scene", agent_id="a2")
    jobs = team_jobs.list_jobs(PROJECT_ID, bid)
    assert [j["id"] for j in jobs] == [b["id"], a["id"]]
    assert a["status"] == "queued" and a["session_id"] == "" and a["cost_micros"] is None


def test_same_helper_cannot_run_twice_on_a_book():
    bid = _book()
    _new(bid)
    with pytest.raises(StoryError) as e:
        _new(bid)
    assert e.value.code == "job_busy" and e.value.status == 409


def test_at_most_three_active_jobs_per_book():
    bid = _book()
    for i in range(team_jobs.MAX_ACTIVE):
        _new(bid, agent_id=f"a{i}")
    with pytest.raises(StoryError) as e:
        _new(bid, agent_id="a9")
    assert e.value.code == "too_many_jobs" and e.value.status == 429


def test_finished_jobs_do_not_block():
    bid = _book()
    j = _new(bid)
    team_jobs.set_running(PROJECT_ID, bid, j["id"], session_id="s-1")
    team_jobs.finish(PROJECT_ID, bid, j["id"], status="done", summary="ok", tokens_in=10, tokens_out=5,
                     cost_micros=42)
    assert _new(bid)["status"] == "queued"


def test_status_only_moves_forward():
    bid = _book()
    j = _new(bid)
    team_jobs.set_running(PROJECT_ID, bid, j["id"], session_id="s-1")
    done = team_jobs.finish(PROJECT_ID, bid, j["id"], status="done", summary="x", tokens_in=1, tokens_out=1,
                            cost_micros=None)
    assert done["status"] == "done" and done["session_id"] == "s-1" and done["finished_at"]
    with pytest.raises(StoryError):
        team_jobs.set_running(PROJECT_ID, bid, j["id"], session_id="s-2")
    again = team_jobs.finish(PROJECT_ID, bid, j["id"], status="error", error="spät")   # Endzustand bleibt
    assert again["status"] == "done"


def test_finish_requires_known_end_status():
    bid = _book()
    j = _new(bid)
    with pytest.raises(StoryError):
        team_jobs.finish(PROJECT_ID, bid, j["id"], status="running")


def test_cancel_request_is_recorded_only_while_active():
    bid = _book()
    j = _new(bid)
    assert team_jobs.request_cancel(PROJECT_ID, bid, j["id"])["cancel_requested"] is True
    team_jobs.finish(PROJECT_ID, bid, j["id"], status="cancelled")
    with pytest.raises(StoryError) as e:
        team_jobs.request_cancel(PROJECT_ID, bid, j["id"])
    assert e.value.code == "job_not_active"


def test_unknown_job_id_and_bad_id():
    bid = _book()
    with pytest.raises(StoryError) as e:
        team_jobs.get(PROJECT_ID, bid, "0" * 32)
    assert e.value.status == 404
    with pytest.raises(StoryError):
        team_jobs.get(PROJECT_ID, bid, "../x")


def test_summary_and_error_are_bounded():
    bid = _book()
    j = _new(bid)
    out = team_jobs.finish(PROJECT_ID, bid, j["id"], status="error", error="x" * 5000, summary="y" * 9000)
    assert len(out["error"]) <= 500 and len(out["summary"]) <= 2000


def test_list_is_bounded():
    bid = _book()
    for i in range(team_jobs.KEEP + 5):
        j = _new(bid, agent_id=f"a{i}")
        team_jobs.finish(PROJECT_ID, bid, j["id"], status="done")
    assert len(team_jobs.list_jobs(PROJECT_ID, bid)) == team_jobs.KEEP


def test_trimming_never_removes_active_jobs():
    """Erst viele fertige, dann aktive anlegen: die aktiven bleiben, die ältesten fertigen gehen."""
    bid = _book()
    for i in range(team_jobs.KEEP):
        team_jobs.finish(PROJECT_ID, bid, _new(bid, agent_id=f"x{i}")["id"], status="done")
    active = [_new(bid, agent_id=f"live{i}") for i in range(team_jobs.MAX_ACTIVE)]
    jobs = team_jobs.list_jobs(PROJECT_ID, bid)
    assert len(jobs) == team_jobs.KEEP
    assert {a["id"] for a in active} <= {j["id"] for j in jobs}
    assert sum(1 for j in jobs if j["status"] == "queued") == team_jobs.MAX_ACTIVE


def test_trimming_keeps_old_active_jobs():
    """Aktive Aufträge, die ganz am Anfang angelegt wurden, überleben viele spätere fertige."""
    bid = _book()
    early = _new(bid, agent_id="früh")
    for i in range(team_jobs.KEEP + 3):
        team_jobs.finish(PROJECT_ID, bid, _new(bid, agent_id=f"x{i}")["id"], status="done")
    ids = {j["id"] for j in team_jobs.list_jobs(PROJECT_ID, bid)}
    assert early["id"] in ids and len(ids) == team_jobs.KEEP


def test_mark_stale_ends_active_jobs_without_live_task():
    bid = _book()
    live, dead = _new(bid, agent_id="a1"), _new(bid, agent_id="a2")
    n = team_jobs.mark_stale(PROJECT_ID, bid, live_ids={live["id"]})
    assert n == 1
    assert team_jobs.get(PROJECT_ID, bid, dead["id"])["status"] == "error"
    assert team_jobs.get(PROJECT_ID, bid, live["id"])["status"] == "queued"


def test_parallel_creates_respect_the_busy_rule():
    bid = _book()
    ok, errors = [], []

    def worker():
        try:
            ok.append(_new(bid))
        except StoryError as e:
            errors.append(e.code)
    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(ok) == 1 and errors == ["job_busy"] * 7
