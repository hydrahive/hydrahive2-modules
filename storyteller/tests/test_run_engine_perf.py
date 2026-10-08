"""A4: Ghostwriter-Lauf – Gedächtnis einmal laden und nachziehen; Dateiarbeit nicht in der Ereignisschleife."""
from __future__ import annotations

import asyncio
import threading

from _ghost_helpers import fake_llm, make_book
from conftest import PROJECT_ID

from backend import ghost, run_engine, runs, storage


def _start(bid, sids):
    return runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="book", scene_ids=sids,
                           model="claude-sonnet-4-6", options={"skip_filled": True, "length_words": 300})


async def test_memory_is_loaded_once_and_sees_the_scenes_written_in_this_run(monkeypatch):
    """Szene 2 muss das Ende der in DIESEM Lauf geschriebenen Szene 1 sehen (Index nachgezogen)."""
    bid, _cid, sids = make_book(3)
    loads = []
    real = ghost.MemoryIndex.load
    monkeypatch.setattr(ghost.MemoryIndex, "load", classmethod(lambda cls, p, b: loads.append(1) or real(p, b)))
    calls = fake_llm(monkeypatch, words=300)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "done"
    assert len(loads) == 1
    second_prompt = calls[1]["messages"][-1]["content"]
    assert "Text1 wort" in second_prompt                   # Ende der eben geschriebenen Szene 1
    third_prompt = calls[2]["messages"][-1]["content"]
    assert "Text2 wort" in third_prompt


async def test_file_work_runs_outside_the_event_loop_thread(monkeypatch):
    """Material bauen und Ablegen dürfen den Server nicht anhalten: sie laufen in einem Hilfs-Thread."""
    bid, _cid, sids = make_book(2)
    loop_thread = threading.get_ident()
    seen: dict[str, set] = {"material": set(), "store": set()}
    real_mat, real_store = ghost.build_material, run_engine._store

    def mat(*a, **k):
        seen["material"].add(threading.get_ident())
        return real_mat(*a, **k)

    def store(*a, **k):
        seen["store"].add(threading.get_ident())
        return real_store(*a, **k)
    monkeypatch.setattr(ghost, "build_material", mat)
    monkeypatch.setattr(run_engine, "_store", store)
    fake_llm(monkeypatch)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "done"
    assert seen["material"] and loop_thread not in seen["material"]
    assert seen["store"] and loop_thread not in seen["store"]


async def test_loop_stays_responsive_while_preparing_a_scene(monkeypatch):
    """Eine langsame Vorbereitung (großes Buch) blockiert andere Aufgaben nicht."""
    import time
    bid, _cid, sids = make_book(1)
    real_mat = ghost.build_material

    def slow(*a, **k):
        time.sleep(0.3)
        return real_mat(*a, **k)
    monkeypatch.setattr(ghost, "build_material", slow)
    fake_llm(monkeypatch)
    run = _start(bid, sids)
    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.02)
            ticks += 1
    t = asyncio.create_task(ticker())
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    t.cancel()
    assert ticks >= 8                                     # bei blockierender Vorbereitung: ~0–2


async def test_written_scene_is_in_the_book(monkeypatch):
    bid, _cid, sids = make_book(1)
    fake_llm(monkeypatch)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert storage.get_scene(PROJECT_ID, bid, sids[0])["text"].startswith("Text1")


async def test_suggest_prepares_context_outside_the_event_loop(monkeypatch):
    """Umschreiben (ai.suggest): Kontext aus den Dateien im Hilfs-Thread."""
    from backend import ai
    bid, _cid, sids = make_book(1, texts={0: "Mia stand am Hafen."})
    loop_thread = threading.get_ident()
    seen = set()
    real = ai._context

    def ctx(*a, **k):
        seen.add(threading.get_ident())
        return real(*a, **k)
    monkeypatch.setattr(ai, "_context", ctx)

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        return "Mia stand am Kai."
    monkeypatch.setattr(ai, "complete", fake_complete)
    out = await ai.suggest("testuser", PROJECT_ID, bid, sids[0], "rewrite", "am Hafen", None)
    assert out["proposal"] == "Mia stand am Kai." and seen and loop_thread not in seen


async def test_suggest_unknown_scene_stays_a_404_and_frees_the_lock():
    from backend import ai
    from backend._files import StoryError
    bid, _cid, _sids = make_book(1)
    import pytest
    with pytest.raises(StoryError) as exc:
        await ai.suggest("testuser", PROJECT_ID, bid, "f" * 32, "rewrite", "x", None)
    assert exc.value.status == 404 and ("testuser", bid) not in ai._busy


async def test_task_killed_mid_run_still_ends_the_run_and_frees_the_lock(monkeypatch):
    """Dienst fährt herunter / Task wird abgebrochen: Endstatus „error“ und die KI-Sperre ist frei."""
    from backend import ai
    bid, _cid, sids = make_book(2)

    async def hook(n):
        await asyncio.sleep(10)
    fake_llm(monkeypatch, hook=hook)
    run = _start(bid, sids)
    key = ai.acquire("testuser", bid)
    task = asyncio.create_task(run_engine.execute(run["id"], PROJECT_ID, bid, "testuser", lock_key=key))
    for _ in range(200):
        if runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "running" and runs.get_run(PROJECT_ID, bid, run["id"])["current_scene"]:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    import pytest
    with pytest.raises(asyncio.CancelledError):
        await task
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "error" and got["error"] == "Lauf wurde beendet" and got["current_scene"] is None
    assert ("testuser", bid) not in ai._busy
    # Der Endstatus steht SOFORT da (nicht erst, wenn ein Hilfs-Thread irgendwann fertig wird).
    from backend import runs as runs_mod
    assert runs_mod.active_run(PROJECT_ID, bid) is None


async def test_run_sees_summary_changes_of_scenes_it_wrote(monkeypatch):
    """Nach jeder geschriebenen Szene wird das Gedächtnis nachgezogen: eine Zusammenfassung, die beim Ablegen
    entsteht/sich ändert, erscheint bei der nächsten Szene."""
    bid, _cid, sids = make_book(2)
    real_store = run_engine._store

    def store(project_id, book_id, scene_id, *a, **k):
        out = real_store(project_id, book_id, scene_id, *a, **k)
        s = storage.get_scene(project_id, book_id, scene_id)
        storage.save_scene(project_id, book_id, scene_id, {"summary": f"NEU-{scene_id[:6]}"}, base_version=s["version"])
        return out
    monkeypatch.setattr(run_engine, "_store", store)
    calls = fake_llm(monkeypatch)
    run = _start(bid, sids)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert f"NEU-{sids[0][:6]}" in calls[1]["messages"][-1]["content"]


async def test_second_cancel_during_cleanup_still_leaves_a_final_status(monkeypatch):
    """Beim Herunterfahren wird ein Task ggf. mehrfach abgebrochen – der Endstatus muss trotzdem stehen
    (darum schreibt der Abbruch-Pfad ihn direkt, ohne await)."""
    from backend import ai
    bid, _cid, sids = make_book(2)

    async def hook(n):
        await asyncio.sleep(10)
    fake_llm(monkeypatch, hook=hook)
    run = _start(bid, sids)
    key = ai.acquire("testuser", bid)
    task = asyncio.create_task(run_engine.execute(run["id"], PROJECT_ID, bid, "testuser", lock_key=key))
    for _ in range(200):
        if runs.get_run(PROJECT_ID, bid, run["id"])["current_scene"]:
            break
        await asyncio.sleep(0.01)
    task.cancel()
    await asyncio.sleep(0)
    task.cancel()                                     # zweiter Abbruch während des Aufräumens
    import pytest
    with pytest.raises(asyncio.CancelledError):
        await task
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "error"
    assert ("testuser", bid) not in ai._busy
