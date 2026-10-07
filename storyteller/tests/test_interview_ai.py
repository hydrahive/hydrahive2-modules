"""Ghostwriter G3: Fragen vorschlagen und Material aus dem Interview (Spec §10.1). LLM gefälscht."""
from __future__ import annotations

import json

import pytest
from conftest import PROJECT_ID

from backend import ghost, interview_ai, interviews, storage
from backend.storage import StoryError


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "Mein Leben am Hafen", "kind": "nonfiction", "language": "de",
                                         "idea": "Erinnerungen eines Hafenarbeiters", "audience": "Familie"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]
    sid = ch["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"summary": "Die ersten Jahre im Hafen."}, base_version=1)
    return b["id"], ch["id"], sid


def _fake(monkeypatch, *answers):
    calls, it = [], iter(answers)

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append(messages)
        return next(it)
    monkeypatch.setattr(interview_ai, "complete", fake_complete)
    return calls


async def test_questions_prompt_uses_chapter_summaries_and_existing(monkeypatch):
    bid, cid, _ = _book()
    interviews.save(PROJECT_ID, bid, cid, [{"id": "a" * 32, "question": "Wann hast du angefangen?", "answer": ""}], base_version=0)
    calls = _fake(monkeypatch, json.dumps({"questions": ["Wie war dein erster Tag?", "Wer war dein Vorarbeiter?"]}))
    qs = await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=2)
    assert qs == ["Wie war dein erster Tag?", "Wer war dein Vorarbeiter?"]
    prompt = calls[0][-1]["content"]
    assert "Kapitel 1" in prompt and "Die ersten Jahre im Hafen." in prompt and "Erinnerungen eines Hafenarbeiters" in prompt
    assert "Wann hast du angefangen?" in prompt          # schon gestellte Fragen: nicht doppelt


@pytest.mark.parametrize("raw", [
    '```json\n{"questions": ["A?", "B?"]}\n```', 'Hier:\n{"questions": ["A?", "B?"]}', '["A?", "B?"]',
])
async def test_questions_parsed_from_text_or_list(monkeypatch, raw):
    bid, cid, _ = _book()
    _fake(monkeypatch, raw)
    assert await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=2) == ["A?", "B?"]


async def test_questions_broken_then_retry_then_fail(monkeypatch):
    bid, cid, _ = _book()
    calls = _fake(monkeypatch, "kein json", '{"questions": ["A?"]}')
    assert await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=1) == ["A?"]
    assert len(calls) == 2
    _fake(monkeypatch, "nein", "auch nicht")
    with pytest.raises(StoryError) as e:
        await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=1)
    assert e.value.code == "questions_invalid"


async def test_questions_are_cleaned_and_limited(monkeypatch):
    bid, cid, _ = _book()
    _fake(monkeypatch, json.dumps({"questions": ["  Eins?  ", "", 5, "x" * 600, *[f"F{i}?" for i in range(12)]]}))
    qs = await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=8)
    assert qs[0] == "Eins?" and len(qs) == 8 and all(isinstance(q, str) and 0 < len(q) <= 500 for q in qs)


async def test_questions_count_range():
    bid, cid, _ = _book()
    for bad in (0, 9):
        with pytest.raises(StoryError):
            await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=bad)


def test_material_with_interview_contains_answers_style_and_no_invention_rule():
    bid, cid, sid = _book()
    long = "Ich bin 1987 nach Hamburg gekommen, mit einem Koffer und sonst nichts. " * 4
    interviews.save(PROJECT_ID, bid, cid, [
        {"id": "a" * 32, "question": "Wann kamst du an?", "answer": long},
        {"id": "b" * 32, "question": "Wer half dir?", "answer": "Mein Onkel Heinz."},
        {"id": "c" * 32, "question": "Unbeantwortet?", "answer": "  "},
    ], base_version=0)
    m = ghost.build_material(PROJECT_ID, bid, sid, interview=interview_ai.interview_material(PROJECT_ID, bid, cid))
    assert "Wann kamst du an?" in m.prompt and "Mein Onkel Heinz." in m.prompt
    assert "Unbeantwortet?" not in m.prompt                                   # leere Antworten fehlen
    assert "STIMME DES AUTORS" in m.prompt and "1987 nach Hamburg" in m.prompt  # Stilprobe wörtlich
    assert "nichts" in m.system.lower() and "erfinde" in m.system.lower()


def test_style_sample_is_bounded():
    bid, cid, sid = _book()
    interviews.save(PROJECT_ID, bid, cid, [{"id": f"{i:032x}", "question": f"F{i}?", "answer": "wort " * 2000}
                                           for i in range(3)], base_version=0)
    iv = interview_ai.interview_material(PROJECT_ID, bid, cid)
    assert len(iv.style_sample) <= interview_ai.STYLE_SAMPLE + 10


def test_interview_allows_missing_summary_but_not_empty_answers():
    bid, cid, sid = _book()
    storage.save_scene(PROJECT_ID, bid, sid, {"summary": ""}, base_version=2)
    empty = interview_ai.interview_material(PROJECT_ID, bid, cid)
    with pytest.raises(StoryError) as e:
        ghost.build_material(PROJECT_ID, bid, sid, interview=empty)
    assert e.value.code == "summary_required"
    interviews.save(PROJECT_ID, bid, cid, [{"id": "a" * 32, "question": "Q?", "answer": "Antwort."}], base_version=0)
    m = ghost.build_material(PROJECT_ID, bid, sid, interview=interview_ai.interview_material(PROJECT_ID, bid, cid))
    assert "Antwort." in m.prompt
