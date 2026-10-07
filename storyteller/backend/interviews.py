"""Ghostwriter G3 – Interview je Kapitel (Spec ghostwriter.md §10.2).

    storyteller/books/<id>/interviews/<kapitel>.json  {chapter_id, version, questions: [{id, question, answer,
                                                        updated_at}], updated_at}
Lesbar für Agenten im Projektordner. Speichern mit Versionsprüfung wie Szenen (veraltet → Conflict, nichts
wird still überschrieben). Ein gelöschtes Kapitel lässt seine Datei liegen (kein stiller Datenverlust).
"""
from __future__ import annotations

from typing import Any

from ._book import Conflict, _existing, _now
from ._files import StoryError, check_id, inside, read_json, write_json

MAX_QUESTIONS = 20
MAX_QUESTION = 500
MAX_ANSWER = 20_000


def _chapters(project_id: str, book_id: str) -> dict[str, str]:
    st = read_json(_existing(project_id, book_id) / "structure.json")
    return {c["id"]: c["title"] for p in st["parts"] for c in p["chapters"]}


def _path(project_id: str, book_id: str, chapter_id: str):
    d = _existing(project_id, book_id)
    check_id(chapter_id, "chapter")
    if chapter_id not in _chapters(project_id, book_id):
        raise StoryError("chapter_not_found", 404)
    return inside(d, "interviews", f"{chapter_id}.json")


def get(project_id: str, book_id: str, chapter_id: str) -> dict:
    path = _path(project_id, book_id, chapter_id)
    if not path.is_file():
        return {"chapter_id": chapter_id, "version": 0, "questions": [], "updated_at": ""}
    return read_json(path)


def _clean(questions: Any, previous: dict[str, dict]) -> list[dict]:
    if not isinstance(questions, list) or len(questions) > MAX_QUESTIONS:
        raise StoryError("interview_invalid")
    out, seen = [], set()
    for q in questions:
        if not isinstance(q, dict):
            raise StoryError("interview_invalid")
        qid = check_id(q.get("id", ""), "question")
        question, answer = q.get("question"), q.get("answer", "")
        if qid in seen or not isinstance(question, str) or not question.strip() or len(question) > MAX_QUESTION:
            raise StoryError("interview_invalid")
        if not isinstance(answer, str) or len(answer) > MAX_ANSWER:
            raise StoryError("interview_invalid")
        seen.add(qid)
        old = previous.get(qid)
        same = old is not None and old["question"] == question.strip() and old["answer"] == answer
        out.append({"id": qid, "question": question.strip(), "answer": answer,
                    "updated_at": old["updated_at"] if same else _now()})
    return out


def save(project_id: str, book_id: str, chapter_id: str, questions: Any, base_version: int) -> dict:
    current = get(project_id, book_id, chapter_id)
    if current["version"] != base_version:
        raise Conflict(current)
    clean = _clean(questions, {q["id"]: q for q in current["questions"]})
    iv = {"chapter_id": chapter_id, "version": current["version"] + 1, "questions": clean, "updated_at": _now()}
    write_json(_path(project_id, book_id, chapter_id), iv)
    return iv


def answered_elsewhere(project_id: str, book_id: str, chapter_id: str) -> list[dict]:
    """Beantwortete Fragen der anderen Kapitel (damit die KI nichts doppelt fragt)."""
    out = []
    for cid, title in _chapters(project_id, book_id).items():
        if cid == chapter_id:
            continue
        for q in get(project_id, book_id, cid)["questions"]:
            if q["answer"].strip():
                out.append({"chapter": title, "question": q["question"], "answer": q["answer"]})
    return out
