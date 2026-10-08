"""A2: Verlauf auch für Infos-, Gliederungs- und Steckbrief-Vorschläge (Spec nichts-geht-verloren.md §2)."""
from __future__ import annotations

from conftest import PROJECT_ID

from backend import _replaced, proposals_entities, proposals_info, proposals_outline, storage

MIA = "e" * 32
OUT_A = {"chapters": [{"title": "Ankunft", "scenes": [{"title": "Die Fähre", "summary": "Mia kommt an."}]}]}
OUT_B = {"chapters": [{"title": "Sturm", "scenes": [{"title": "Die Nacht", "summary": "Ein Sturm zieht auf."}]}]}


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": MIA, "kind": "character", "name": "Mia", "aliases": [], "description": "Zwölf.", "fields": []}]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    sid = st["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"title": "Alt", "summary": "Alt."}, base_version=1)
    return b["id"], sid, s


def test_info_replace_discard_restore():
    bid, sid, s = _book()
    a = proposals_info.store(PROJECT_ID, bid, sid, {"title": "Erster"}, base_version=s["version"], author="B — Struktur")
    assert a["replaced_from"] is None
    b = proposals_info.store(PROJECT_ID, bid, sid, {"title": "Zweiter"}, base_version=s["version"], author="B — Lektor")
    assert b["replaced_from"]["author"] == "B — Struktur"
    proposals_info.discard(PROJECT_ID, bid, sid)
    hist = _replaced.history(PROJECT_ID, bid, "info", sid)
    assert [(h["fields"]["title"], h["reason"]) for h in hist] == [("Zweiter", "discarded"), ("Erster", "replaced")]
    back = proposals_info.restore(PROJECT_ID, bid, sid, hist[1]["id"])
    assert back["fields"] == {"title": "Erster"} and proposals_info.get(PROJECT_ID, bid, sid)["fields"]["title"] == "Erster"
    assert [h["fields"]["title"] for h in _replaced.history(PROJECT_ID, bid, "info", sid)] == ["Zweiter"]


def test_info_accept_does_not_go_to_history():
    bid, sid, s = _book()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    proposals_info.accept(PROJECT_ID, bid, sid, base_version=s["version"])
    assert _replaced.history(PROJECT_ID, bid, "info", sid) == []


def test_outline_replace_and_discard_keep():
    bid, _sid, _s = _book()
    assert proposals_outline.store(PROJECT_ID, bid, OUT_A, author="B — Kreativ")["replaced_from"] is None
    second = proposals_outline.store(PROJECT_ID, bid, OUT_B, author="B — Struktur")
    assert second["replaced_from"]["author"] == "B — Kreativ"
    proposals_outline.discard(PROJECT_ID, bid)
    hist = _replaced.history(PROJECT_ID, bid, "outline", "outline")
    assert [h["reason"] for h in hist] == ["discarded", "replaced"] and all(h["chapters"] == 1 for h in hist)
    back = proposals_outline.restore(PROJECT_ID, bid, hist[1]["id"])
    assert back["outline"]["chapters"][0]["title"] == "Ankunft"
    assert proposals_outline.get(PROJECT_ID, bid)["outline"]["chapters"][0]["title"] == "Ankunft"


def test_entity_change_replace_and_discard_keep():
    bid, _sid, _s = _book()
    proposals_entities.store(PROJECT_ID, bid, MIA, {"description": "A"}, author="B — Steckbrief-Pfleger")
    b = proposals_entities.store(PROJECT_ID, bid, MIA, {"description": "B"})
    assert b["replaced_from"]["author"] == "B — Steckbrief-Pfleger"
    proposals_entities.discard(PROJECT_ID, bid, b["id"])
    hist = _replaced.history(PROJECT_ID, bid, "entity", MIA)
    assert [h["reason"] for h in hist] == ["discarded", "replaced"]
    assert proposals_entities.list_for_book(PROJECT_ID, bid) == []
    back = proposals_entities.restore(PROJECT_ID, bid, MIA, hist[1]["id"])
    assert back["changes"] == {"description": "A"}
    assert [p["changes"] for p in proposals_entities.list_for_book(PROJECT_ID, bid)] == [{"description": "A"}]


def test_new_entity_discard_goes_under_new():
    bid, _sid, _s = _book()
    p = proposals_entities.store(PROJECT_ID, bid, None, {"kind": "character", "name": "Hinnerk"})
    assert p["replaced_from"] is None
    proposals_entities.discard(PROJECT_ID, bid, p["id"])
    hist = _replaced.history(PROJECT_ID, bid, "entity", "new")
    assert len(hist) == 1 and hist[0]["name"] == "Hinnerk" and hist[0]["reason"] == "discarded"


def test_restoring_a_new_entity_whose_name_now_exists_fails_and_keeps_the_entry():
    import pytest
    from backend._files import StoryError
    bid, _sid, _s = _book()
    p = proposals_entities.store(PROJECT_ID, bid, None, {"kind": "character", "name": "Hinnerk"})
    proposals_entities.discard(PROJECT_ID, bid, p["id"])
    h = _replaced.history(PROJECT_ID, bid, "entity", "new")[0]
    st = storage.get_structure(PROJECT_ID, bid)
    st["entities"].append({"id": "f" * 32, "kind": "character", "name": "Hinnerk", "aliases": [], "description": "",
                           "fields": []})
    storage.save_structure(PROJECT_ID, bid, st, base_version=st["version"])
    with pytest.raises(StoryError) as exc:
        proposals_entities.restore(PROJECT_ID, bid, "new", h["id"])
    assert exc.value.code == "entity_exists"
    assert len(_replaced.history(PROJECT_ID, bid, "entity", "new")) == 1
