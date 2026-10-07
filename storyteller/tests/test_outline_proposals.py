"""Ghostwriter G4d: Gliederungs-Vorschlag des Agenten – Ablage, Übernehmen (bearbeitete Fassung), Verwerfen."""
from __future__ import annotations

import pytest
from backend import proposals_outline as po
from backend import storage
from backend._files import StoryError
from backend.storage import Conflict
from conftest import PROJECT_ID

OUT = {"chapters": [{"title": "Ankunft", "scenes": [{"title": "Die Fähre", "summary": "Mia kommt an."},
                                                   {"title": "Der Turm", "summary": "Hinnerk zeigt ihr den Turm.", "pov": "Mia"}]},
                    {"title": "Sturm", "scenes": [{"title": "Die Nacht", "summary": "Ein Sturm zieht auf."}]}],
       "entities": [{"name": "Hinnerk", "kind": "character", "description": "Großvater."}]}


def _book(with_text=False):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    if with_text:
        sid = st["parts"][0]["chapters"][0]["scenes"][0]
        storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Schon geschrieben."}, base_version=1)
    return b["id"], storage.get_structure(PROJECT_ID, b["id"])


def test_store_validates_and_leaves_book_untouched():
    bid, st = _book()
    p = po.store(PROJECT_ID, bid, OUT, source="agent", session_id="s1", note="drei Szenen")
    assert p["outline"]["chapters"][1]["title"] == "Sturm" and p["base_structure_version"] == st["version"]
    assert p["source"] == "agent" and p["session_id"] == "s1" and p["note"] == "drei Szenen"
    assert po.get(PROJECT_ID, bid)["outline"] == p["outline"] and storage.get_structure(PROJECT_ID, bid) == st


def test_store_replaces_and_rejects_invalid():
    bid, _ = _book()
    po.store(PROJECT_ID, bid, OUT)
    po.store(PROJECT_ID, bid, {"chapters": [{"title": "Nur eins", "scenes": [{"title": "S", "summary": "x"}]}]})
    assert [c["title"] for c in po.get(PROJECT_ID, bid)["outline"]["chapters"]] == ["Nur eins"]
    for bad in ({}, {"chapters": []}, {"chapters": [{"title": "K", "scenes": []}]},
                {"chapters": [{"title": "K", "scenes": [{"title": "S", "summary": ""}]}]}):
        with pytest.raises(StoryError) as exc:
            po.store(PROJECT_ID, bid, bad)
        assert exc.value.code == "outline_invalid"
    with pytest.raises(StoryError):
        po.store(PROJECT_ID, bid, OUT, source="hacker")


def test_accept_edited_version_appends_and_removes_proposal():
    bid, st = _book(with_text=True)
    po.store(PROJECT_ID, bid, OUT)
    edited = {**OUT, "chapters": [{**OUT["chapters"][0], "title": "Ankunft (bearbeitet)"}]}      # Kapitel 2 gestrichen
    r = po.accept(PROJECT_ID, bid, edited, base_version=st["version"])
    titles = [c["title"] for p in r["structure"]["parts"] for c in p["chapters"]]
    assert titles[-1] == "Ankunft (bearbeitet)" and "Sturm" not in titles and len(titles) == 2      # angehängt
    assert len(r["scenes"]) == 2 and any(e["name"] == "Hinnerk" for e in r["structure"]["entities"])
    with pytest.raises(StoryError) as exc:
        po.get(PROJECT_ID, bid)
    assert exc.value.code == "proposal_not_found"


def test_accept_on_new_book_replaces_empty_start_scene():
    bid, st = _book()
    lone = st["parts"][0]["chapters"][0]["scenes"][0]
    po.store(PROJECT_ID, bid, OUT)
    r = po.accept(PROJECT_ID, bid, OUT, base_version=st["version"])
    ids = [s for p in r["structure"]["parts"] for c in p["chapters"] for s in c["scenes"]]
    assert lone not in ids and len(ids) == 3


def test_accept_conflict_invalid_and_without_proposal_keep_book():
    bid, st = _book()
    po.store(PROJECT_ID, bid, OUT)
    with pytest.raises(Conflict):
        po.accept(PROJECT_ID, bid, OUT, base_version=st["version"] - 1)
    with pytest.raises(StoryError):
        po.accept(PROJECT_ID, bid, {"chapters": []}, base_version=st["version"])
    assert po.get(PROJECT_ID, bid) and storage.get_structure(PROJECT_ID, bid) == st          # Vorschlag bleibt
    po.discard(PROJECT_ID, bid)
    with pytest.raises(StoryError) as exc:
        po.accept(PROJECT_ID, bid, OUT, base_version=st["version"])
    assert exc.value.code == "proposal_not_found" and storage.get_structure(PROJECT_ID, bid) == st


def test_scene_limit_counts_existing_scenes(monkeypatch):
    import backend.outline as outline_mod
    bid, st = _book(with_text=True)
    po.store(PROJECT_ID, bid, OUT)
    monkeypatch.setattr(outline_mod, "MAX_SCENES", 3)                      # 1 vorhanden + 3 neu > 3
    with pytest.raises(StoryError) as exc:
        po.accept(PROJECT_ID, bid, OUT, base_version=st["version"])
    assert exc.value.code == "too_many_scenes" and po.get(PROJECT_ID, bid)


def test_text_and_info_lists_ignore_outline_file_even_with_outline_md():
    """Gegen die Teilstring-Falle *.json: auch wenn zufällig eine outline.md daneben liegt."""
    from backend import proposals, proposals_info
    bid, _ = _book()
    po.store(PROJECT_ID, bid, OUT)
    (storage.book_dir(PROJECT_ID, bid) / "proposals" / "outline.md").write_text("x", encoding="utf-8")
    assert proposals.list_for_book(PROJECT_ID, bid) == [] and proposals_info.list_for_book(PROJECT_ID, bid) == []
