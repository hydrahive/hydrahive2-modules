"""T1d: Hinweise/Notizen des Schreib-Teams am Buch (Spec schreib-team.md §5, Plan schreib-team-t1d.md)."""
from __future__ import annotations

import threading

import pytest

from backend import storage, team_notes
from backend._files import StoryError
from conftest import PROJECT_ID


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]
    st["entities"] = [{"id": "e" * 32, "kind": "character", "name": "Mia", "aliases": [], "description": "", "fields": []}]
    storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    return b["id"], ch["id"], ch["scenes"][0]


def _add(bid, **kw):
    base = {"kind": "hint", "title": "Augenfarbe", "text": "Kap. 1 blau, Steckbrief grün.", "author": "Plausibilität",
            "agent_id": "a1", "session_id": "s1"}
    return team_notes.add(PROJECT_ID, bid, {**base, **kw})


def test_add_hint_at_scene_and_list_open():
    bid, cid, sid = _book()
    n = _add(bid, scene_id=sid)
    assert n["status"] == "open" and n["scene_id"] == sid and n["kind"] == "hint" and len(n["id"]) == 32
    assert n["author"] == "Plausibilität" and n["agent_id"] == "a1" and n["session_id"] == "s1" and n["at"]
    got = team_notes.list_notes(PROJECT_ID, bid)
    assert [x["id"] for x in got] == [n["id"]]


def test_note_with_sources_chapter_and_entity():
    bid, cid, sid = _book()
    n = _add(bid, kind="note", chapter_id=cid, title="Lotsenwesen", text="Seit 1900 …",
             sources=[{"title": "Wiki", "url": "https://de.wikipedia.org/wiki/Lotse"}])
    assert n["kind"] == "note" and n["chapter_id"] == cid and n["sources"][0]["url"].startswith("https://")
    e = _add(bid, entity_id="e" * 32)
    assert e["entity_id"] == "e" * 32


@pytest.mark.parametrize("bad", [
    {"kind": "lob"}, {"title": ""}, {"title": "x" * 201}, {"text": ""}, {"text": "x" * 4001},
    {"sources": [{"url": "javascript:alert(1)"}]}, {"sources": [{"url": "ftp://x"}]},
    {"sources": [{"url": f"https://x/{i}"} for i in range(11)]}, {"sources": "kaputt"},
])
def test_invalid_fields_are_refused(bad):
    bid, _cid, _sid = _book()
    with pytest.raises(StoryError) as exc:
        _add(bid, **bad)
    assert exc.value.code == "note_invalid"


def test_place_must_exist():
    bid, cid, sid = _book()
    for place in ({"scene_id": "f" * 32}, {"chapter_id": "f" * 32}, {"entity_id": "f" * 32}):
        with pytest.raises(StoryError) as exc:
            _add(bid, **place)
        assert exc.value.code == "place_not_found"


def test_limit_of_open_notes(monkeypatch):
    bid, _cid, _sid = _book()
    monkeypatch.setattr(team_notes, "MAX_OPEN", 2)
    a = _add(bid)
    _add(bid)
    with pytest.raises(StoryError) as exc:
        _add(bid)
    assert exc.value.code == "too_many_notes"
    team_notes.set_status(PROJECT_ID, bid, a["id"], "done")      # erledigte zählen nicht
    _add(bid)


def test_status_filter_order_and_counts():
    bid, cid, sid = _book()
    a = _add(bid, scene_id=sid, title="a")
    b = _add(bid, scene_id=sid, title="b")
    c = _add(bid, title="c")
    team_notes.set_status(PROJECT_ID, bid, a["id"], "done")
    assert [x["title"] for x in team_notes.list_notes(PROJECT_ID, bid)] == ["b", "c"]          # Standard: offen
    assert [x["title"] for x in team_notes.list_notes(PROJECT_ID, bid, status="all")] == ["a", "b", "c"]
    assert [x["title"] for x in team_notes.list_notes(PROJECT_ID, bid, scene_id=sid)] == ["b"]
    assert team_notes.open_counts(PROJECT_ID, bid) == {sid: 1}
    team_notes.set_status(PROJECT_ID, bid, b["id"], "dismissed")
    assert team_notes.open_counts(PROJECT_ID, bid) == {}
    with pytest.raises(StoryError):
        team_notes.set_status(PROJECT_ID, bid, c["id"], "vielleicht")


def test_delete_and_unknown_ids():
    bid, _cid, _sid = _book()
    n = _add(bid)
    team_notes.delete(PROJECT_ID, bid, n["id"])
    assert team_notes.list_notes(PROJECT_ID, bid, status="all") == []
    for fn in (lambda: team_notes.delete(PROJECT_ID, bid, n["id"]),
               lambda: team_notes.set_status(PROJECT_ID, bid, "../../etc", "done")):
        with pytest.raises(StoryError):
            fn()


def test_parallel_adds_from_several_helpers_all_land():
    bid, _cid, _sid = _book()
    errors = []

    def worker(i):
        try:
            _add(bid, title=f"t{i}", author=f"H{i % 3}")
        except Exception as e:  # noqa: BLE001
            errors.append(e)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(team_notes.list_notes(PROJECT_ID, bid)) == 20


def test_unknown_book_is_404():
    with pytest.raises(StoryError) as exc:
        team_notes.list_notes(PROJECT_ID, "f" * 32)
    assert exc.value.status == 404
