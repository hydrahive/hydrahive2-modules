"""Ghostwriter G2: Lauf-Schleife (Spec §9.2/§9.3/§9.4). LLM gefälscht – geprüft wird das Verhalten."""
from __future__ import annotations

import asyncio

from _ghost_helpers import fake_llm, make_book
from conftest import PROJECT_ID

from backend import ai, proposals, run_engine, runs, storage


def _book(n_scenes=3, **kw):
    bid, _, sids = make_book(n_scenes, **kw)
    return bid, sids


_fake = fake_llm


def _start(bid, sids, *, skip_filled=True):
    run = runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="book", scene_ids=sids,
                          model="claude-sonnet-4-6", options={"skip_filled": skip_filled, "length_words": 300})
    return run


def _scene(bid, sid):
    return storage.get_scene(PROJECT_ID, bid, sid)


async def test_empty_scenes_are_written_directly_with_origin_and_status(monkeypatch):
    bid, sids = _book(2)
    calls = _fake(monkeypatch)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "done"
    assert [p["state"] for p in got["progress"]] == ["written", "written"]
    assert all(p["words"] == 300 for p in got["progress"])
    assert got["current_scene"] is None and got["error"] is None
    for sid in sids:
        s = _scene(bid, sid)
        assert s["text"].startswith("Text") and s["origin"] == "ai_draft" and s["status"] == "draft"
    assert len(calls) == 2 and all(c["model"] == "claude-sonnet-4-6" for c in calls)
    assert got["tokens_out"] > 0 and got["cost_micros"] and got["cost_micros"] > 0


async def test_next_scene_sees_end_of_previous(monkeypatch):
    bid, sids = _book(2)
    calls = _fake(monkeypatch)
    await run_engine.execute(_start(bid, sids)["id"], PROJECT_ID, bid, "testuser")
    assert "Text1" in calls[1]["messages"][1]["content"]


async def test_filled_scene_skipped_or_becomes_proposal(monkeypatch):
    bid, sids = _book(2, texts={1: "Eigener Text."})
    _fake(monkeypatch)
    r1 = _start(bid, sids, skip_filled=True)
    await run_engine.execute(r1["id"], PROJECT_ID, bid, "testuser")
    assert runs.get_run(PROJECT_ID, bid, r1["id"])["progress"][1]["state"] == "skipped_filled"
    assert _scene(bid, sids[1])["text"] == "Eigener Text."
    assert proposals.list_for_book(PROJECT_ID, bid) == []

    r2 = _start(bid, [sids[1]], skip_filled=False)
    await run_engine.execute(r2["id"], PROJECT_ID, bid, "testuser")
    assert runs.get_run(PROJECT_ID, bid, r2["id"])["progress"][0]["state"] == "proposal"
    assert _scene(bid, sids[1])["text"] == "Eigener Text."
    assert proposals.get(PROJECT_ID, bid, sids[1])["text"].startswith("Text")


async def test_scene_changed_during_run_becomes_proposal(monkeypatch):
    bid, sids = _book(1)

    async def author_types(n):
        s = _scene(bid, sids[0])
        storage.save_scene(PROJECT_ID, bid, sids[0], {"text": "Autor war schneller."}, base_version=s["version"])
    _fake(monkeypatch, hook=author_types)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert runs.get_run(PROJECT_ID, bid, run["id"])["progress"][0]["state"] == "proposal"
    assert _scene(bid, sids[0])["text"] == "Autor war schneller."
    assert proposals.get(PROJECT_ID, bid, sids[0])["text"].startswith("Text")


async def test_scene_without_summary_is_skipped(monkeypatch):
    bid, sids = _book(2, summaries={0: ""})
    calls = _fake(monkeypatch)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert [p["state"] for p in got["progress"]] == ["skipped_no_summary", "written"]
    assert len(calls) == 1


async def test_limit_stops_before_scene_that_would_exceed(monkeypatch):
    # Länge 300 Wörter → Schätzung ca. 480 Ausgabe-Tokens je Szene; Grenze 1000 → 2 Szenen ok, die dritte nicht.
    bid, sids = _book(3, length=300, limit=1000)
    calls = _fake(monkeypatch, words=300)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "limit"
    assert [p["state"] for p in got["progress"]] == ["written", "written", "waiting"]
    assert len(calls) == 2


async def test_model_error_marks_scene_and_run(monkeypatch):
    bid, sids = _book(2)
    _fake(monkeypatch, fail_on=1)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "error" and "Modell weg" in got["error"]
    assert got["progress"][0]["state"] == "error" and got["progress"][1]["state"] == "waiting"
    assert _scene(bid, sids[0])["text"] == ""


async def test_lock_is_held_during_run_and_released_after(monkeypatch):
    bid, sids = _book(1)
    seen = {}

    async def check(n):
        seen["busy"] = ("testuser", bid) in ai._busy
    _fake(monkeypatch, hook=check)
    key = ai.acquire("testuser", bid)
    await run_engine.execute(_start(bid, sids)["id"], PROJECT_ID, bid, "testuser", lock_key=key)
    assert seen["busy"] is True
    assert ("testuser", bid) not in ai._busy


async def test_lock_released_even_on_crash(monkeypatch):
    bid, sids = _book(1)
    _fake(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("kaputt")
    monkeypatch.setattr(run_engine.ghost, "build_material", boom)
    key = ai.acquire("testuser", bid)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser", lock_key=key)
    assert ("testuser", bid) not in ai._busy
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "error"


async def test_memory_written_after_scene_when_summary_empty_is_not_needed_but_kept(monkeypatch):
    """Autor-Zusammenfassung wird nie ersetzt (die Szene hatte ja eine, sonst wäre sie übersprungen)."""
    bid, sids = _book(1, summaries={0: "Vom Autor."})
    _fake(monkeypatch)
    await run_engine.execute(_start(bid, sids)["id"], PROJECT_ID, bid, "testuser")
    assert _scene(bid, sids[0])["summary"] == "Vom Autor."


async def test_start_in_background_names_task_for_recovery(monkeypatch):
    bid, sids = _book(1)
    gate = asyncio.Event()

    async def wait(n):
        await gate.wait()
    _fake(monkeypatch, hook=wait)
    run = _start(bid, sids)
    task = run_engine.start_background(run["id"], PROJECT_ID, bid, "testuser", lock_key=None)
    await asyncio.sleep(0.05)
    assert task.get_name() == f"{runs.RUN_TASK_PREFIX}{run['id']}"
    await runs.recover_stale_runs()                      # (verwaiste Läufe anderer Tests dürfen bereinigt werden)
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "running"   # lebender Lauf wird nicht angefasst
    gate.set()
    await task
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "done"
