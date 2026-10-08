"""A2: Ghostwriter-Lauf ersetzt einen offenen Vorschlag – sichtbar im Fortschritt, der alte bleibt im Verlauf."""
from __future__ import annotations


from _ghost_helpers import fake_llm, make_book
from conftest import PROJECT_ID

from backend import proposals, run_engine, runs, storage


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


async def test_replacing_an_open_proposal_is_marked_in_progress(monkeypatch):
    """A2: Liegt schon ein Vorschlag (z. B. vom Lektor) an der Szene, ersetzt ihn der Lauf – sichtbar im Fortschritt
    (``replaced``: von wem); der alte bleibt im Verlauf."""
    from backend import _replaced
    bid, sids = _book(1, texts={0: "Eigener Text."})
    s = _scene(bid, sids[0])
    proposals.store(PROJECT_ID, bid, sids[0], "Vom Lektor.", run_id="", model="", base_version=s["version"],
                    source="agent", author="T — Lektor")
    _fake(monkeypatch)
    r = _start(bid, sids, skip_filled=False)
    await run_engine.execute(r["id"], PROJECT_ID, bid, "testuser")
    p = runs.get_run(PROJECT_ID, bid, r["id"])["progress"][0]
    assert p["state"] == "proposal" and p["replaced"] == "T — Lektor"
    hist = _replaced.history(PROJECT_ID, bid, "text", sids[0])
    assert len(hist) == 1 and hist[0]["author"] == "T — Lektor" and hist[0]["replaced_by"] == "Ghostwriter-Lauf"
