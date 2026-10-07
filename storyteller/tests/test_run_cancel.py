"""Ghostwriter G2: Abbrechen eines Laufs (Spec §9.2) – nach einer Szene, mitten im Stream, zwischen Szenen."""
from __future__ import annotations

import re

from _ghost_helpers import fake_llm, make_book
from conftest import PROJECT_ID

from backend import run_engine, runs, storage


def _book(n_scenes=3, **kw):
    bid, _, sids = make_book(n_scenes, **kw)
    return bid, sids


_fake = fake_llm


def _start(bid, sids):
    return runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="book", scene_ids=sids,
                           model="claude-sonnet-4-6", options={"skip_filled": True, "length_words": 300})


def _scene(bid, sid):
    return storage.get_scene(PROJECT_ID, bid, sid)


async def test_cancel_after_first_scene_stops_without_further_calls(monkeypatch):
    bid, sids = _book(3)
    calls = _fake(monkeypatch)
    run = _start(bid, sids)

    async def cancel_after_first(n):
        if n == 2:
            run_engine.cancel(run["id"])
    _fake(monkeypatch, calls=calls, hook=cancel_after_first)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "cancelled"
    assert got["progress"][0]["state"] == "written"
    assert got["progress"][2]["state"] == "waiting"
    assert len(calls) == 2                       # der laufende Aufruf wurde abgebrochen, kein dritter
    assert _scene(bid, sids[1])["text"] == ""    # halber Text landet nicht in der Szene
    assert _scene(bid, sids[2])["text"] == ""


async def test_cancel_while_streaming_stops_the_stream(monkeypatch):
    """Abbruch mitten im Modellaufruf: der Stream wird nicht zu Ende gelesen (Verbindung zu)."""
    bid, sids = _book(1, length=300)
    run = _start(bid, sids)
    read = []
    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        for i, part in enumerate(re.findall(r"\S+\s*", "wort " * 300)):
            read.append(i)
            if i == 100:                     # nach dem Anfangspuffer (~400 Zeichen) von write_scene
                run_engine.cancel(run["id"])
            yield part
    monkeypatch.setattr(run_engine.ghost, "stream", fake_stream)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert runs.get_run(PROJECT_ID, bid, run["id"])["status"] == "cancelled"
    assert len(read) <= 102                     # sofort nach dem Abbruch Schluss, nicht bis Wort 300
    assert _scene(bid, sids[0])["text"] == ""


async def test_cancel_between_scenes_starts_no_new_scene(monkeypatch):
    """Abbruch, nachdem eine Szene fertig ist und bevor die nächste beginnt."""
    bid, sids = _book(2)
    calls = _fake(monkeypatch)
    run = _start(bid, sids)
    real_store = run_engine._store

    def store_then_cancel(*a, **k):
        state = real_store(*a, **k)
        run_engine.cancel(run["id"])
        return state
    monkeypatch.setattr(run_engine, "_store", store_then_cancel)
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "cancelled" and len(calls) == 1
    assert [p["state"] for p in got["progress"]] == ["written", "waiting"]
