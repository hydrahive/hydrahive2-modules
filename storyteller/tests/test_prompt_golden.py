"""A5: Golden-Test – die deutschen Prompts eines Romans bleiben beim Umzug nach _texts.py unverändert.

Erzeugt einmal mit 0.17.0 (STORYTELLER_GOLDEN=write), danach nur Vergleich. Gedächtnis kurz genug, dass kein
Kürzen greift (der Zeilenschnitt ist eine gewollte Änderung, eigener Test)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from conftest import PROJECT_ID

from backend import ai, ghost, interview_ai, interviews, outline, storage

GOLDEN = Path(__file__).parent / "golden" / "prompts_de_novel.json"


def _book(kind="novel"):
    b = storage.create_book(PROJECT_ID, {"title": "Der Leuchtturm", "kind": kind, "language": "de", "audience": "Erwachsene",
                                         "idea": "Mia, Lotsentochter auf Helgoland."})
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": "e" * 32, "kind": "character", "name": "Mia", "aliases": [], "description": "Zwölf.",
                       "fields": [{"key": "Augen", "value": "blau"}]}]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    ch = st["parts"][0]["chapters"][0]
    s1 = ch["scenes"][0]
    s2 = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "Der Brief", after=s1)["scene"]["id"]
    storage.save_scene(PROJECT_ID, b["id"], s1, {"title": "Am Hafen", "summary": "Mia sieht das Boot ablegen.",
                                                  "text": "Mia stand am Hafen. Der Wind war kalt. Es regnete lange."},
                       base_version=storage.get_scene(PROJECT_ID, b["id"], s1)["version"])
    storage.save_scene(PROJECT_ID, b["id"], s2, {"summary": "Mia findet einen Brief.", "pov": "Mia",
                                                  "text": "Im Turm lag ein Brief."},
                       base_version=storage.get_scene(PROJECT_ID, b["id"], s2)["version"])
    storage.update_book(PROJECT_ID, b["id"], {"ghost": {"style": "Präteritum, ruhig.", "length_words": 300}},
                        base_version=storage.get_book(PROJECT_ID, b["id"])["version"])
    return b["id"], ch["id"], s1, s2


async def _collect(monkeypatch, kind="novel"):
    bid, cid, s1, s2 = _book(kind)
    seen: dict[str, list] = {}

    async def fake_stream(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.setdefault("ghost", []).append(messages)
        yield "Text " * 150

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        seen.setdefault("complete", []).append(messages)
        return '{"questions": ["Wie war es?"]}' if "interview" in json.dumps(messages).lower() else "Kurz."
    monkeypatch.setattr(ghost, "stream", fake_stream)
    monkeypatch.setattr(ghost, "complete", fake_complete)
    monkeypatch.setattr(ai, "complete", fake_complete)
    monkeypatch.setattr(interview_ai, "complete", fake_complete)
    monkeypatch.setattr(outline, "complete", fake_complete)
    out = {}
    m = ghost.build_material(PROJECT_ID, bid, s2)
    out["material_s2"] = {"system": m.system, "prompt": m.prompt}
    out["material_s1"] = {"system": ghost.build_material(PROJECT_ID, bid, s1).system,
                          "prompt": ghost.build_material(PROJECT_ID, bid, s1).prompt}
    gen = ghost.write_scene(m, model=None, length_words=600, chunk_words=300)
    async for _ in gen:
        pass
    out["ghost_sections"] = seen["ghost"]
    seen["complete"] = []
    for action in ai.ACTIONS:
        await ai.suggest("u", PROJECT_ID, bid, s1, action, "Der Wind war kalt." if action != "continue" else "Es regnete", None)
    out["suggest"] = seen["complete"]
    seen["complete"] = []
    s = storage.get_scene(PROJECT_ID, bid, s1)
    storage.save_scene(PROJECT_ID, bid, s1, {"summary": ""}, base_version=s["version"])
    await ghost.summarize_scene(PROJECT_ID, bid, s1)
    out["summarize"] = seen["complete"]
    seen["complete"] = []
    iv = interviews.get(PROJECT_ID, bid, cid)
    interviews.save(PROJECT_ID, bid, cid, [{"id": "a" * 32, "question": "Wie war der Hafen?", "answer": "Laut und nass."}],
                    base_version=iv["version"])
    await interview_ai.suggest_questions(PROJECT_ID, bid, cid, count=2)
    out["interview"] = seen["complete"]
    seen["complete"] = []
    with pytest.raises(Exception):          # die Antwort „Kurz.“ ist kein JSON – hier zählt nur der Prompt
        await outline.generate(PROJECT_ID, bid, idea="Mia", chapters=1, scenes_per_chapter=2)
    out["outline"] = seen["complete"][:1]
    iv_mat = interview_ai.interview_material(PROJECT_ID, bid, cid)
    m_iv = ghost.build_material(PROJECT_ID, bid, s2, interview=iv_mat)
    out["material_interview"] = {"system": m_iv.system, "prompt": m_iv.prompt}
    return json.loads(json.dumps(out))


async def test_german_novel_prompts_are_unchanged(monkeypatch):
    got = await _collect(monkeypatch)
    if os.environ.get("STORYTELLER_GOLDEN") == "write":
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(got, ensure_ascii=False, indent=1), encoding="utf-8")
        pytest.skip("Golden geschrieben")
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert set(got) == set(want)
    for key in want:
        assert got[key] == want[key], key
