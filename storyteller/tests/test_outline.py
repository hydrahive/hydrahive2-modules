"""Ghostwriter G2: Gliederung aus Idee (Spec §9.1). LLM gefälscht."""
from __future__ import annotations

import json

import pytest
from conftest import PROJECT_ID

from backend import outline, storage
from backend.storage import Conflict, StoryError

GOOD = {
    "chapters": [
        {"title": "Ankunft", "scenes": [
            {"title": "Am Bahnhof", "summary": "Mia kommt an und niemand holt sie ab.", "pov": "Mia"},
            {"title": "Das Haus", "summary": "Das Haus der Tante ist verlassen."}]},
        {"title": "Spuren", "scenes": [{"title": "Der Brief", "summary": "Mia findet einen Brief."}]},
    ],
    "entities": [{"name": "Mia", "kind": "character", "description": "Zwölf, neugierig."},
                 {"name": "Tante Ilse", "kind": "character", "description": "Verschwunden."}],
}


def _book(kind="novel"):
    return storage.create_book(PROJECT_ID, {"title": "Leuchtturm", "kind": kind, "language": "de",
                                            "idea": "Ein Mädchen sucht ihre Tante."})


def _fake(monkeypatch, *answers):
    calls = []
    it = iter(answers)

    async def fake_complete(messages, model=None, temperature=0.7, max_tokens=4096):
        calls.append({"messages": messages, "model": model, "max_tokens": max_tokens})
        return next(it)
    monkeypatch.setattr(outline, "complete", fake_complete)
    return calls


async def test_generate_prompt_contains_idea_kind_language_and_size(monkeypatch):
    b = _book()
    calls = _fake(monkeypatch, json.dumps(GOOD))
    out = await outline.generate(PROJECT_ID, b["id"], idea="", chapters=2, scenes_per_chapter=2, hints="düster")
    prompt = calls[0]["messages"][-1]["content"]
    assert "Ein Mädchen sucht ihre Tante." in prompt and "düster" in prompt
    assert "2 Kapitel" in prompt and "2 Szenen" in prompt
    assert "Roman" in calls[0]["messages"][0]["content"] and "Deutsch" in calls[0]["messages"][0]["content"]
    assert out == outline.validate(GOOD)


@pytest.mark.parametrize("wrap", [
    "```json\n{j}\n```", "Hier ist die Gliederung:\n{j}\nViel Spaß!", "{j}",
])
async def test_json_is_found_in_code_block_or_text(monkeypatch, wrap):
    b = _book()
    _fake(monkeypatch, wrap.replace("{j}", json.dumps(GOOD)))
    out = await outline.generate(PROJECT_ID, b["id"], idea="x", chapters=2, scenes_per_chapter=2)
    assert [c["title"] for c in out["chapters"]] == ["Ankunft", "Spuren"]


async def test_broken_json_asks_once_more_then_fails(monkeypatch):
    b = _book()
    calls = _fake(monkeypatch, "kein json", json.dumps(GOOD))
    out = await outline.generate(PROJECT_ID, b["id"], idea="x", chapters=2, scenes_per_chapter=2)
    assert len(calls) == 2 and out["chapters"]
    _fake(monkeypatch, "kaputt {", "immer noch nicht")
    with pytest.raises(StoryError) as e:
        await outline.generate(PROJECT_ID, b["id"], idea="x", chapters=2, scenes_per_chapter=2)
    assert e.value.code == "outline_invalid"


@pytest.mark.parametrize("bad", [
    {"chapters": []},
    {"chapters": [{"title": "", "scenes": [{"title": "a", "summary": "b"}]}]},
    {"chapters": [{"title": "K", "scenes": []}]},
    {"chapters": [{"title": "K", "scenes": [{"title": "a", "summary": "x" * 2001}]}]},
    {"chapters": [{"title": "K" * 201, "scenes": [{"title": "a", "summary": "b"}]}]},
    {"chapters": [{"title": "K", "scenes": [{"title": "a", "summary": "b"}] * 9}]},
    {"chapters": [{"title": "K", "scenes": [{"title": "a", "summary": "b"}]}] * 41},
    {"chapters": "nein"},
    {"chapters": [{"title": "K", "scenes": ["nur text"]}]},
    {"chapters": [{"title": "K", "scenes": [{"title": "a", "summary": "  "}]}]},
])
def test_validate_rejects(bad):
    with pytest.raises(StoryError):
        outline.validate(bad)


def test_validate_pov_null_is_empty():
    out = outline.validate({"chapters": [{"title": "K", "scenes": [{"title": "a", "summary": "b", "pov": None}]}]})
    assert out["chapters"][0]["scenes"][0]["pov"] == ""


def test_validate_cleans_entities():
    out = outline.validate({**GOOD, "entities": [{"name": "X", "kind": "drache"}, {"name": "", "kind": "place"},
                                                 {"name": "Ort", "kind": "place", "description": 5}]})
    assert out["entities"] == [{"name": "X", "kind": "character", "description": ""},
                               {"name": "Ort", "kind": "place", "description": ""}]


def test_apply_to_empty_book_replaces_the_empty_scene():
    b = _book()
    st0 = storage.get_structure(PROJECT_ID, b["id"])
    empty = st0["parts"][0]["chapters"][0]["scenes"][0]
    res = outline.apply(PROJECT_ID, b["id"], outline.validate(GOOD), base_version=st0["version"])
    st = res["structure"]
    chapters = st["parts"][0]["chapters"]
    assert [c["title"] for c in chapters] == ["Ankunft", "Spuren"]
    assert empty not in [s for c in chapters for s in c["scenes"]]
    s0 = storage.get_scene(PROJECT_ID, b["id"], chapters[0]["scenes"][0])
    assert (s0["title"], s0["summary"], s0["pov"], s0["text"], s0["origin"]) == (
        "Am Bahnhof", "Mia kommt an und niemand holt sie ab.", "Mia", "", "human")
    assert {e["name"] for e in st["entities"]} == {"Mia", "Tante Ilse"}
    assert set(res["scenes"]) == {s for c in chapters for s in c["scenes"]}


def test_apply_to_book_with_content_appends_and_keeps_existing_entities():
    b = _book()
    st0 = storage.get_structure(PROJECT_ID, b["id"])
    first = st0["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], first, {"text": "Schon geschrieben."}, base_version=1)
    st0["entities"] = [{"id": "e" * 32, "kind": "character", "name": "Mia", "aliases": [], "description": "alt",
                        "fields": []}]
    st0 = storage.save_structure(PROJECT_ID, b["id"], st0, base_version=st0["version"])
    st = outline.apply(PROJECT_ID, b["id"], outline.validate(GOOD), base_version=st0["version"])["structure"]
    chapters = st["parts"][-1]["chapters"]
    assert chapters[0]["scenes"] == [first] and [c["title"] for c in chapters[1:]] == ["Ankunft", "Spuren"]
    mia = [e for e in st["entities"] if e["name"] == "Mia"]
    assert len(mia) == 1 and mia[0]["description"] == "alt"
    assert storage.get_scene(PROJECT_ID, b["id"], first)["text"] == "Schon geschrieben."


def test_apply_checks_structure_version():
    b = _book()
    st0 = storage.get_structure(PROJECT_ID, b["id"])
    with pytest.raises(Conflict):
        outline.apply(PROJECT_ID, b["id"], outline.validate(GOOD), base_version=st0["version"] - 1)
    assert storage.get_structure(PROJECT_ID, b["id"]) == st0


def test_apply_respects_scene_limit(monkeypatch):
    b = _book()
    monkeypatch.setattr(outline, "MAX_SCENES", 2)
    st0 = storage.get_structure(PROJECT_ID, b["id"])
    with pytest.raises(StoryError) as e:
        outline.apply(PROJECT_ID, b["id"], outline.validate(GOOD), base_version=st0["version"])
    assert e.value.code == "too_many_scenes"
    assert storage.get_structure(PROJECT_ID, b["id"]) == st0
