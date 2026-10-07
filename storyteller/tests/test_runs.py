"""Ghostwriter G2: Lauf-Datensätze (module_storyteller_runs) und Bereinigung nach Neustart (Spec §9.2)."""
from __future__ import annotations

import asyncio

import pytest
from conftest import OTHER_PROJECT_ID, PROJECT_ID

from backend import runs

RESTART = "Durch Neustart abgebrochen – bitte neu starten"


def _new(book="b" * 32, scenes=("s1" * 16, "s2" * 16), user="testuser", project=PROJECT_ID):
    return runs.create_run(user=user, project_id=project, book_id=book, scope="book",
                           scene_ids=list(scenes), model="m", options={"skip_filled": True})


def test_create_run_has_waiting_progress_per_scene():
    r = _new()
    assert r["status"] == "queued" and r["model"] == "m" and r["scope"] == "book"
    assert [p["state"] for p in r["progress"]] == ["waiting", "waiting"]
    assert r["tokens_out"] == 0 and r["tokens_in"] == 0 and r["cost_micros"] is None
    assert r["options"] == {"skip_filled": True}


def test_get_run_only_in_own_project_and_book():
    r = _new(book="c" * 32)
    assert runs.get_run(PROJECT_ID, "c" * 32, r["id"])["id"] == r["id"]
    assert runs.get_run(OTHER_PROJECT_ID, "c" * 32, r["id"]) is None
    assert runs.get_run(PROJECT_ID, "d" * 32, r["id"]) is None


def test_active_run_only_queued_or_running():
    book = "e" * 32
    assert runs.active_run(PROJECT_ID, book) is None
    r = _new(book=book)
    assert runs.active_run(PROJECT_ID, book)["id"] == r["id"]
    runs.update_run(r["id"], status="running")
    assert runs.active_run(PROJECT_ID, book)["id"] == r["id"]
    runs.update_run(r["id"], status="done")
    assert runs.active_run(PROJECT_ID, book) is None


def test_set_scene_state_and_counters():
    r = _new(book="f" * 32)
    sid = r["progress"][1]["scene_id"]
    runs.set_scene_state(r["id"], sid, "written", words=812)
    runs.add_usage(r["id"], tokens_in=1000, tokens_out=1300, cost_micros=2100)
    runs.add_usage(r["id"], tokens_in=500, tokens_out=200, cost_micros=None)
    got = runs.get_run(PROJECT_ID, "f" * 32, r["id"])
    assert got["progress"][1] == {"scene_id": sid, "state": "written", "words": 812}
    assert got["progress"][0]["state"] == "waiting"
    # Kosten bleiben bekannt, wenn ein Teil ohne Tarif ist? Nein: einmal unbekannt → Summe unbekannt wäre falsch
    # gerundet; wir zählen nur bekannte Teile und merken, dass etwas fehlte.
    assert (got["tokens_in"], got["tokens_out"]) == (1500, 1500)
    assert got["cost_micros"] == 2100 and got["cost_partial"] is True


def test_update_run_can_clear_fields():
    r = _new(book="a7" * 16)
    runs.update_run(r["id"], current_scene="x" * 32, error="alt")
    runs.update_run(r["id"], current_scene=None, error=None)
    got = runs.get_run(PROJECT_ID, "a7" * 16, r["id"])
    assert got["current_scene"] is None and got["error"] is None


def test_update_run_ignores_unknown_fields():
    r = _new(book="a1" * 16)
    runs.update_run(r["id"], status="error", error="x", project_id="hack")
    got = runs.get_run(PROJECT_ID, "a1" * 16, r["id"])
    assert got["status"] == "error" and got["error"] == "x" and got["project_id"] == PROJECT_ID


def test_latest_run_of_book():
    book = "a2" * 16
    assert runs.latest_run(PROJECT_ID, book) is None
    _new(book=book)
    r2 = _new(book=book)
    assert runs.latest_run(PROJECT_ID, book)["id"] == r2["id"]


async def test_recovery_marks_orphans_and_keeps_live_runs():
    orphan = _new(book="a3" * 16)
    runs.update_run(orphan["id"], status="running")
    done = _new(book="a4" * 16)
    runs.update_run(done["id"], status="done")
    live = _new(book="a5" * 16)
    release = asyncio.Event()

    async def _live():
        await release.wait()

    task = asyncio.create_task(_live(), name=f"{runs.RUN_TASK_PREFIX}{live['id']}")
    await asyncio.sleep(0)
    changed = await runs.recover_stale_runs()
    release.set()
    await task
    assert changed >= 1
    o = runs.get_run(PROJECT_ID, "a3" * 16, orphan["id"])
    assert (o["status"], o["error"]) == ("error", RESTART)
    assert runs.get_run(PROJECT_ID, "a4" * 16, done["id"])["status"] == "done"
    assert runs.get_run(PROJECT_ID, "a5" * 16, live["id"])["status"] == "queued"


def test_run_rejects_too_many_scenes():
    with pytest.raises(ValueError):
        _new(book="a6" * 16, scenes=[f"{i:032x}" for i in range(runs.MAX_RUN_SCENES + 1)])
