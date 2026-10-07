"""Ghostwriter G3: Kapitel aus dem Interview schreiben – Lauf mit Quelle „interview“ (Spec §10.1 Schritt 3)."""
from __future__ import annotations

import pytest
from _ghost_helpers import fake_llm
from conftest import PROJECT_ID

from backend import interviews, proposals, run_engine, run_plan, runs, storage
from backend.storage import StoryError


def _book(summaries=("", "")):
    b = storage.create_book(PROJECT_ID, {"title": "Hafen", "kind": "nonfiction", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]
    sids = [ch["scenes"][0], storage.add_scene(PROJECT_ID, b["id"], ch["id"], "Abschnitt 2", after=ch["scenes"][0])["scene"]["id"]]
    for sid, summ in zip(sids, summaries):
        if summ:
            storage.save_scene(PROJECT_ID, b["id"], sid, {"summary": summ}, base_version=1)
    storage.update_book(PROJECT_ID, b["id"], {"ghost": {"model": "claude-sonnet-4-6", "length_words": 300}}, base_version=b["version"])
    return b["id"], ch["id"], sids


def _answer(bid, cid, text="Ich kam 1987 mit einem Koffer nach Hamburg."):
    interviews.save(PROJECT_ID, bid, cid, [{"id": "a" * 32, "question": "Wie kamst du an?", "answer": text}], base_version=0)


def test_plan_with_interview_counts_scenes_without_summary():
    bid, cid, sids = _book()
    _answer(bid, cid)
    p = run_plan.plan(PROJECT_ID, bid, scope="chapter", chapter_id=cid, source="interview")
    assert p["scene_ids"] == sids and p["skipped_no_summary"] == 0
    normal = run_plan.plan(PROJECT_ID, bid, scope="chapter", chapter_id=cid)
    assert normal["scene_ids"] == [] and normal["skipped_no_summary"] == 2


def test_plan_interview_needs_answers_and_chapter_scope():
    bid, cid, _ = _book()
    with pytest.raises(StoryError) as e:
        run_plan.plan(PROJECT_ID, bid, scope="chapter", chapter_id=cid, source="interview")
    assert e.value.code == "interview_empty"
    _answer(bid, cid)
    with pytest.raises(StoryError) as e:
        run_plan.plan(PROJECT_ID, bid, scope="book", source="interview")
    assert e.value.code == "interview_needs_chapter"


async def test_run_from_interview_writes_with_answers_in_prompt(monkeypatch):
    bid, cid, sids = _book(summaries=("Ankunft.", ""))
    _answer(bid, cid)
    calls = fake_llm(monkeypatch)
    run = runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="chapter", scene_ids=sids,
                          model="claude-sonnet-4-6", options={"skip_filled": True, "length_words": 300,
                                                              "source": "interview", "chapter_id": cid})
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    got = runs.get_run(PROJECT_ID, bid, run["id"])
    assert got["status"] == "done" and [p["state"] for p in got["progress"]] == ["written", "written"]
    assert all("1987 mit einem Koffer nach Hamburg" in c["messages"][1]["content"] for c in calls)
    assert all("Erfinde nichts" in c["messages"][0]["content"] for c in calls)
    for sid in sids:
        assert storage.get_scene(PROJECT_ID, bid, sid)["origin"] == "ai_draft"


async def test_interview_run_keeps_existing_text_as_proposal(monkeypatch):
    bid, cid, sids = _book()
    _answer(bid, cid)
    storage.save_scene(PROJECT_ID, bid, sids[0], {"text": "Mein eigener Text."}, base_version=1)
    fake_llm(monkeypatch)
    run = runs.create_run(user="testuser", project_id=PROJECT_ID, book_id=bid, scope="chapter", scene_ids=sids,
                          model="m", options={"skip_filled": False, "length_words": 300, "source": "interview", "chapter_id": cid})
    await run_engine.execute(run["id"], PROJECT_ID, bid, "testuser")
    assert storage.get_scene(PROJECT_ID, bid, sids[0])["text"] == "Mein eigener Text."
    assert proposals.get(PROJECT_ID, bid, sids[0])["text"].startswith("Text")
