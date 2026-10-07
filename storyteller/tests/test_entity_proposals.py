"""Ghostwriter G4c: Steckbrief-Vorschläge (neu/ändern) – Ablage, Übernehmen, Verwerfen."""
from __future__ import annotations

import pytest
from conftest import PROJECT_ID

from backend import proposals_entities as pe
from backend import storage
from backend._files import StoryError
from backend.storage import Conflict

MIA = "e" * 32


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": MIA, "kind": "character", "name": "Mia", "aliases": ["Mi"], "description": "Zwölf.",
                       "fields": [{"key": "Augen", "value": "grün"}]}]
    st = storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    return b["id"], st


def test_new_entity_proposal_and_accept_creates_it():
    bid, st = _book()
    p = pe.store(PROJECT_ID, bid, None, {"kind": "character", "name": "Hinnerk", "aliases": ["Großvater"],
                                         "description": "Leuchtturmwärter."}, source="agent", session_id="s", note="neu")
    assert p["entity_id"] == "" and p["changes"]["name"] == "Hinnerk" and p["base_structure_version"] == st["version"]
    assert storage.get_structure(PROJECT_ID, bid) == st                                  # nichts geändert
    new_st = pe.accept(PROJECT_ID, bid, p["id"], base_version=st["version"])
    h = next(e for e in new_st["entities"] if e["name"] == "Hinnerk")
    assert h["kind"] == "character" and h["aliases"] == ["Großvater"] and h["fields"] == [] and h["id"] != MIA
    assert new_st["version"] == st["version"] + 1 and pe.list_for_book(PROJECT_ID, bid) == []


def test_change_proposal_only_changed_fields_and_accept():
    bid, st = _book()
    p = pe.store(PROJECT_ID, bid, MIA, {"name": "Mia", "description": "Zwölf, mutig.", "fields": [{"key": "Augen", "value": "grün"},
                                                                                                    {"key": "Haare", "value": "rot"}]})
    assert set(p["changes"]) == {"description", "fields"} and p["kind"] == "character"
    new_st = pe.accept(PROJECT_ID, bid, p["id"], base_version=st["version"])
    m = next(e for e in new_st["entities"] if e["id"] == MIA)
    assert m["description"] == "Zwölf, mutig." and m["aliases"] == ["Mi"] and len(m["fields"]) == 2


def test_rejections():
    bid, st = _book()
    cases = [
        (None, {"name": "Ohne Art"}, "entity_invalid"),
        (None, {"kind": "monster", "name": "X"}, "entity_invalid"),
        (None, {"kind": "place"}, "entity_invalid"),
        (None, {"kind": "character", "name": "mia"}, "entity_exists"),               # gibt es schon (Name)
        (None, {"kind": "character", "name": "MI"}, "entity_exists"),                # … oder als Spitzname
        (MIA, {"name": "Mia", "description": "Zwölf."}, "nothing_changed"),
        ("f" * 32, {"description": "x"}, "entity_not_found"),
        (MIA, {"description": "x" * 10_001}, "entity_invalid"),
        (MIA, {"aliases": "kein Array"}, "entity_invalid"),
        (MIA, {"fields": [{"key": "k", "value": 5}]}, "entity_invalid"),
        (MIA, {"kind": "place"}, "nothing_changed"),                                 # Art ändern gibt es nicht
    ]
    for eid, changes, code in cases:
        with pytest.raises(StoryError) as exc:
            pe.store(PROJECT_ID, bid, eid, changes)
        assert exc.value.code == code, (eid, changes, exc.value.code)
    with pytest.raises(StoryError):
        pe.store(PROJECT_ID, bid, MIA, {"description": "x"}, source="hacker")
    assert pe.list_for_book(PROJECT_ID, bid) == []


def test_one_open_change_per_entity_replaces_and_exists_error_names_id():
    bid, _ = _book()
    a = pe.store(PROJECT_ID, bid, MIA, {"description": "A"})
    b = pe.store(PROJECT_ID, bid, MIA, {"description": "B"})
    assert [p["id"] for p in pe.list_for_book(PROJECT_ID, bid)] == [b["id"]] and a["id"] != b["id"]
    with pytest.raises(StoryError) as exc:
        pe.store(PROJECT_ID, bid, None, {"kind": "character", "name": "Mia"})
    assert MIA in str(exc.value.detail)


def test_accept_conflict_deleted_entity_and_discard():
    bid, st = _book()
    p = pe.store(PROJECT_ID, bid, MIA, {"description": "Neu"})
    with pytest.raises(Conflict):
        pe.accept(PROJECT_ID, bid, p["id"], base_version=st["version"] - 1)
    st2 = dict(st, entities=[])
    st2 = storage.save_structure(PROJECT_ID, bid, st2, base_version=st["version"])      # Autor löscht Mia
    with pytest.raises(StoryError) as exc:
        pe.accept(PROJECT_ID, bid, p["id"], base_version=st2["version"])
    assert exc.value.code == "entity_not_found" and pe.get(PROJECT_ID, bid, p["id"])        # bleibt sichtbar
    pe.discard(PROJECT_ID, bid, p["id"])
    assert pe.list_for_book(PROJECT_ID, bid) == []
    for bad in ("f" * 32, "../x"):
        with pytest.raises(StoryError):
            pe.get(PROJECT_ID, bid, bad)


def test_new_limit():
    bid, _ = _book()
    for i in range(pe.MAX_NEW):
        pe.store(PROJECT_ID, bid, None, {"kind": "item", "name": f"Ding {i}"})
    with pytest.raises(StoryError) as exc:
        pe.store(PROJECT_ID, bid, None, {"kind": "item", "name": "Eins zu viel"})
    assert exc.value.code == "too_many_proposals"


def test_accept_validates_against_entity_limit(monkeypatch):
    from backend import _structure
    bid, st = _book()
    p = pe.store(PROJECT_ID, bid, None, {"kind": "place", "name": "Leuchtturm"})
    monkeypatch.setattr(_structure, "MAX_ENTITIES", 1)
    with pytest.raises(StoryError):
        pe.accept(PROJECT_ID, bid, p["id"], base_version=st["version"])
    assert storage.get_structure(PROJECT_ID, bid)["version"] == st["version"]
