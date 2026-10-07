"""Ghostwriter G3: Interview-Ablage je Kapitel (Spec §10.2): interviews/<kapitel>.json mit Version."""
from __future__ import annotations

import json

import pytest
from conftest import PROJECT_ID

from backend import interviews, storage
from backend.storage import Conflict, StoryError


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "Mein Leben", "kind": "nonfiction", "language": "de"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    return b["id"], ch["id"]


def _q(qid, question="Wo bist du aufgewachsen?", answer=""):
    return {"id": qid, "question": question, "answer": answer}


def test_new_chapter_has_empty_interview():
    bid, cid = _book()
    iv = interviews.get(PROJECT_ID, bid, cid)
    assert iv == {"chapter_id": cid, "version": 0, "questions": [], "updated_at": ""}


def test_save_increments_version_and_is_readable_file():
    bid, cid = _book()
    iv = interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, answer="In Hamburg, 1987.")], base_version=0)
    assert iv["version"] == 1 and iv["questions"][0]["answer"] == "In Hamburg, 1987." and iv["questions"][0]["updated_at"]
    raw = json.loads((storage.book_dir(PROJECT_ID, bid) / "interviews" / f"{cid}.json").read_text())
    assert raw["questions"][0]["question"] == "Wo bist du aufgewachsen?"
    iv2 = interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, answer="In Hamburg.")], base_version=1)
    assert iv2["version"] == 2


def test_unchanged_answer_keeps_its_timestamp():
    bid, cid = _book()
    iv = interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, answer="A"), _q("b" * 32, answer="B")], base_version=0)
    t_a = iv["questions"][0]["updated_at"]
    iv2 = interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, answer="A"), _q("b" * 32, answer="B neu")], base_version=1)
    assert iv2["questions"][0]["updated_at"] == t_a


def test_outdated_version_conflicts_and_keeps_data():
    bid, cid = _book()
    interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, answer="erste")], base_version=0)
    with pytest.raises(Conflict) as e:
        interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, answer="zweite")], base_version=0)
    assert e.value.current["questions"][0]["answer"] == "erste"
    assert interviews.get(PROJECT_ID, bid, cid)["questions"][0]["answer"] == "erste"


@pytest.mark.parametrize("bad", [
    [_q("a" * 32, question="")],
    [_q("a" * 32, question="x" * 501)],
    [_q("a" * 32, answer="x" * 20_001)],
    [_q("../x")],
    [_q("a" * 32), _q("a" * 32)],
    [_q(f"{i:032x}") for i in range(21)],
    ["kein dict"],
    [{"id": "a" * 32, "question": "Q", "answer": 5}],
])
def test_limits_and_shape(bad):
    bid, cid = _book()
    with pytest.raises(StoryError):
        interviews.save(PROJECT_ID, bid, cid, bad, base_version=0)
    assert interviews.get(PROJECT_ID, bid, cid)["version"] == 0


def test_unknown_chapter_and_path_protection():
    bid, _ = _book()
    with pytest.raises(StoryError) as e:
        interviews.get(PROJECT_ID, bid, "f" * 32)
    assert e.value.status == 404
    for bad in ("../../x", "a" * 31):
        with pytest.raises(StoryError):
            interviews.get(PROJECT_ID, bid, bad)


def test_answers_of_other_chapters():
    bid, cid = _book()
    st = storage.get_structure(PROJECT_ID, bid)
    c2 = storage.add_chapter(PROJECT_ID, bid, st["parts"][0]["id"], "Kapitel 2", "Abschnitt 1")
    cid2 = c2["structure"]["parts"][0]["chapters"][1]["id"]
    interviews.save(PROJECT_ID, bid, cid, [_q("a" * 32, "Frage 1", "Antwort 1"), _q("b" * 32, "Frage 2", "")], base_version=0)
    other = interviews.answered_elsewhere(PROJECT_ID, bid, cid2)
    assert other == [{"chapter": "Kapitel 1", "question": "Frage 1", "answer": "Antwort 1"}]
    assert interviews.answered_elsewhere(PROJECT_ID, bid, cid) == []
