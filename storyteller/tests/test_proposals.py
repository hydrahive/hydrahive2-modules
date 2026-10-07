"""Ghostwriter G2: abgelegte Vorschläge (Spec §9.3). Die Szene bleibt unberührt, bis der Autor übernimmt."""
from __future__ import annotations

import pytest
from conftest import PROJECT_ID

from backend import proposals, snapshots, storage
from backend.storage import Conflict, StoryError


def _book_with_text(text="Mein Text."):
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": text}, base_version=1)
    return b["id"], sid, s


def test_store_does_not_touch_scene_and_is_readable():
    bid, sid, s = _book_with_text()
    info = proposals.store(PROJECT_ID, bid, sid, "KI-Fassung.", run_id="r1", model="m", base_version=s["version"])
    assert info["scene_id"] == sid and info["words"] == 1 and info["run_id"] == "r1"
    assert storage.get_scene(PROJECT_ID, bid, sid) == s
    got = proposals.get(PROJECT_ID, bid, sid)
    assert got["text"] == "KI-Fassung." and got["model"] == "m" and got["base_version"] == s["version"]
    d = storage.book_dir(PROJECT_ID, bid)
    assert (d / "proposals" / f"{sid}.md").read_text() == "KI-Fassung."


def test_new_proposal_replaces_old_and_list():
    bid, sid, s = _book_with_text()
    proposals.store(PROJECT_ID, bid, sid, "alt", run_id="r1", model="m", base_version=s["version"])
    proposals.store(PROJECT_ID, bid, sid, "neu und länger", run_id="r2", model="m", base_version=s["version"])
    assert proposals.get(PROJECT_ID, bid, sid)["text"] == "neu und länger"
    assert [p["scene_id"] for p in proposals.list_for_book(PROJECT_ID, bid)] == [sid]


def test_accept_snapshots_old_text_sets_ai_draft_and_removes_proposal():
    bid, sid, s = _book_with_text("Alter Text vom Autor.")
    proposals.store(PROJECT_ID, bid, sid, "KI-Fassung.", run_id="r1", model="m", base_version=s["version"])
    scene = proposals.accept(PROJECT_ID, bid, sid, base_version=s["version"])
    assert scene["text"] == "KI-Fassung." and scene["origin"] == "ai_draft" and scene["version"] == s["version"] + 1
    snaps = storage.list_snapshots(PROJECT_ID, bid, sid)
    assert snaps and snapshots.get_snapshot(PROJECT_ID, bid, sid, snaps[0]["id"])["text"] == "Alter Text vom Autor."
    with pytest.raises(StoryError):
        proposals.get(PROJECT_ID, bid, sid)


def test_accept_with_outdated_version_conflicts_and_changes_nothing():
    bid, sid, s = _book_with_text()
    proposals.store(PROJECT_ID, bid, sid, "KI", run_id="r1", model="m", base_version=s["version"])
    s2 = storage.save_scene(PROJECT_ID, bid, sid, {"text": "inzwischen geändert"}, base_version=s["version"])
    with pytest.raises(Conflict):
        proposals.accept(PROJECT_ID, bid, sid, base_version=s["version"])
    assert storage.get_scene(PROJECT_ID, bid, sid)["text"] == "inzwischen geändert"
    assert proposals.get(PROJECT_ID, bid, sid)["text"] == "KI"
    # mit aktueller Version geht es
    assert proposals.accept(PROJECT_ID, bid, sid, base_version=s2["version"])["text"] == "KI"


def test_discard_only_removes_proposal():
    bid, sid, s = _book_with_text("bleibt")
    proposals.store(PROJECT_ID, bid, sid, "weg", run_id="r1", model="m", base_version=s["version"])
    proposals.discard(PROJECT_ID, bid, sid)
    assert storage.get_scene(PROJECT_ID, bid, sid)["text"] == "bleibt"
    assert proposals.list_for_book(PROJECT_ID, bid) == []
    proposals.discard(PROJECT_ID, bid, sid)   # zweimal: kein Fehler


@pytest.mark.parametrize("bad", ["../x", "a" * 31, "Z" * 32, "..", "a" * 32 + "/../b"])
def test_invalid_scene_ids_are_rejected(bad):
    """Erst die ID-Prüfung (scene_invalid), der Pfadschutz ist nur die zweite Sicherung."""
    bid, _, _ = _book_with_text()
    for call in (lambda: proposals.store(PROJECT_ID, bid, bad, "x", run_id="r", model="", base_version=1),
                 lambda: proposals.get(PROJECT_ID, bid, bad), lambda: proposals.discard(PROJECT_ID, bid, bad)):
        with pytest.raises(StoryError) as e:
            call()
        assert e.value.code == "scene_invalid"


def test_unknown_scene_is_rejected():
    bid, _, _ = _book_with_text()
    with pytest.raises(StoryError):
        proposals.store(PROJECT_ID, bid, "f" * 32, "x", run_id="r", model="", base_version=1)


def test_too_long_proposal_is_rejected():
    bid, sid, s = _book_with_text()
    with pytest.raises(StoryError):
        proposals.store(PROJECT_ID, bid, sid, "x" * (storage.MAX_SCENE_BYTES + 1), run_id="r", model="", base_version=1)
