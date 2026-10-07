"""Ghostwriter G4b: Vorschläge für Szenen-Infos (Titel, Zusammenfassung, Perspektive) – Ablage, Übernehmen, Verwerfen."""
from __future__ import annotations

import pytest
from backend import proposals, proposals_info, storage
from backend._files import StoryError
from backend.storage import Conflict
from conftest import PROJECT_ID


def _scene():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"title": "Alt", "summary": "Alte Zusammenfassung.", "text": "Text."},
                           base_version=1)
    return b["id"], sid, s


def test_store_and_get_only_changed_fields_scene_untouched():
    bid, sid, s = _scene()
    info = proposals_info.store(PROJECT_ID, bid, sid, {"title": "Alt", "summary": "Neue Zusammenfassung.", "pov": "Mia"},
                                base_version=s["version"], source="agent", session_id="s1", note="genauer")
    assert info["fields"] == {"summary": "Neue Zusammenfassung.", "pov": "Mia"}      # „title“ unverändert → weg
    assert info["source"] == "agent" and info["session_id"] == "s1" and info["note"] == "genauer"
    assert proposals_info.get(PROJECT_ID, bid, sid)["fields"] == info["fields"]
    assert storage.get_scene(PROJECT_ID, bid, sid) == s


def test_nothing_changed_and_invalid_fields_rejected():
    bid, sid, s = _scene()
    for fields, code in (({"title": "Alt"}, "nothing_changed"), ({}, "nothing_changed"),
                         ({"summary": "x" * 2001}, "summary_invalid"), ({"title": 5}, "title_invalid"),
                         ({"status": "done"}, "nothing_changed"), ({"text": "Hack"}, "nothing_changed")):
        with pytest.raises(StoryError) as exc:
            proposals_info.store(PROJECT_ID, bid, sid, fields, base_version=s["version"])
        assert exc.value.code == code, fields
    with pytest.raises(StoryError):
        proposals_info.store(PROJECT_ID, bid, sid, {"title": "N"}, base_version=s["version"], source="hacker")
    assert proposals_info.list_for_book(PROJECT_ID, bid) == []


def test_text_and_info_proposals_coexist_and_listing():
    bid, sid, s = _scene()
    proposals.store(PROJECT_ID, bid, sid, "Neuer Text", run_id="", model="", base_version=s["version"], source="agent")
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"], source="agent")
    assert [p["scene_id"] for p in proposals.list_for_book(PROJECT_ID, bid)] == [sid]   # Text-Liste unverändert
    infos = proposals_info.list_for_book(PROJECT_ID, bid)
    assert [(i["scene_id"], i["fields"]) for i in infos] == [(sid, {"title": "Neu"})]
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neuer"}, base_version=s["version"])
    assert proposals_info.get(PROJECT_ID, bid, sid)["fields"] == {"title": "Neuer"}     # ersetzt


def test_accept_all_or_selected_fields_with_version_check():
    bid, sid, s = _scene()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu", "summary": "Neu zusammengefasst."}, base_version=s["version"])
    saved = proposals_info.accept(PROJECT_ID, bid, sid, base_version=s["version"], fields=["summary"])
    assert saved["summary"] == "Neu zusammengefasst." and saved["title"] == "Alt" and saved["origin"] == s["origin"]
    assert saved["text"] == "Text." and saved["version"] == s["version"] + 1
    with pytest.raises(StoryError) as exc:
        proposals_info.get(PROJECT_ID, bid, sid)
    assert exc.value.code == "proposal_not_found"


def test_accept_conflict_and_unknown_field_and_empty_selection():
    bid, sid, s = _scene()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    with pytest.raises(Conflict):
        proposals_info.accept(PROJECT_ID, bid, sid, base_version=s["version"] - 1)
    for bad in (["text"], [], ["pov"]):                    # pov nicht im Vorschlag, text nie erlaubt, leer
        with pytest.raises(StoryError):
            proposals_info.accept(PROJECT_ID, bid, sid, base_version=s["version"], fields=bad)
    assert proposals_info.get(PROJECT_ID, bid, sid)["fields"] == {"title": "Neu"}       # bleibt bei Fehler
    assert storage.get_scene(PROJECT_ID, bid, sid)["title"] == "Alt"


def test_discard_and_trash_takes_info_proposal_along():
    bid, sid, s = _scene()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    proposals_info.discard(PROJECT_ID, bid, sid)
    assert proposals_info.list_for_book(PROJECT_ID, bid) == []
    ch = storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"][0]["id"]
    other = storage.add_scene(PROJECT_ID, bid, ch, "Zweite")["scene"]["id"]
    proposals_info.store(PROJECT_ID, bid, other, {"summary": "Weg damit"}, base_version=1)
    storage.remove_scene(PROJECT_ID, bid, other)
    trash = storage.story_root(PROJECT_ID) / "trash" / bid / "scenes"
    t = next(p for p in trash.iterdir() if p.name.startswith(other))
    assert (t / "proposal.info.json").is_file()
    assert proposals_info.list_for_book(PROJECT_ID, bid) == []


def test_unknown_scene_and_bad_ids():
    bid, _, _ = _scene()
    for sid in ("f" * 32, "../x"):
        with pytest.raises(StoryError):
            proposals_info.store(PROJECT_ID, bid, sid, {"title": "N"}, base_version=1)


def test_text_list_ignores_info_even_if_a_meta_md_exists():
    """Gegen die Teilstring-Falle: *.json trifft auch <szene>.meta.json."""
    bid, sid, s = _scene()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    (storage.book_dir(PROJECT_ID, bid) / "proposals" / f"{sid}.meta.md").write_text("x", encoding="utf-8")
    assert proposals.list_for_book(PROJECT_ID, bid) == []
