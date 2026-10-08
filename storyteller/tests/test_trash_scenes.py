"""A3: gelöschte Szenen aus dem Papierkorb wiederherstellen (Spec nichts-geht-verloren.md §3)."""
from __future__ import annotations

import json

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import _replaced, proposals, snapshots, storage, trash
from backend._files import StoryError

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book():
    """Kapitel 1: A, B, C. B hat Text, Schnappschuss, offenen Vorschlag und einen im Verlauf."""
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    a = ch["scenes"][0]
    bb = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "B", after=a)["scene"]["id"]
    c = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "C", after=bb)["scene"]["id"]
    s = storage.save_scene(PROJECT_ID, b["id"], bb, {"text": "Wichtiger Text von B.", "summary": "B passiert."}, base_version=1)
    snapshots.add_snapshot(PROJECT_ID, b["id"], bb, "Ältere Fassung")
    proposals.store(PROJECT_ID, b["id"], bb, "Früher", run_id="r0", model="m", base_version=s["version"])
    proposals.store(PROJECT_ID, b["id"], bb, "Offen", run_id="r1", model="m", base_version=s["version"])
    return b["id"], ch["id"], [a, bb, c]


def _order(bid):
    return [c["scenes"] for p in storage.get_structure(PROJECT_ID, bid)["parts"] for c in p["chapters"]]


def test_delete_remembers_place_and_list_shows_it():
    bid, cid, (a, bb, _c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    rows = trash.list_scenes(PROJECT_ID, bid)
    assert len(rows) == 1
    r = rows[0]
    assert r["scene_id"] == bb and r["title"] == "B" and r["chapter_id"] == cid and r["after"] == a
    assert r["chapter_exists"] is True and r["words"] == 4 and r["deleted_at"] and r["id"].startswith(bb)


def test_restore_puts_scene_back_at_its_place_with_everything():
    bid, _cid, (a, bb, c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    out = trash.restore_scene(PROJECT_ID, bid, trash.list_scenes(PROJECT_ID, bid)[0]["id"])
    assert out["placed"] == "original" and out["scene"]["id"] == bb
    assert _order(bid) == [[a, bb, c]]
    s = storage.get_scene(PROJECT_ID, bid, bb)
    assert s["text"] == "Wichtiger Text von B." and s["summary"] == "B passiert."
    assert [x["words"] for x in snapshots.list_snapshots(PROJECT_ID, bid, bb)] == [2]
    assert proposals.get(PROJECT_ID, bid, bb)["text"] == "Offen"
    assert len(_replaced.history(PROJECT_ID, bid, "text", bb)) == 1
    assert trash.list_scenes(PROJECT_ID, bid) == []
    assert out["structure"]["version"] == storage.get_structure(PROJECT_ID, bid)["version"]


def test_restore_when_neighbour_is_gone_goes_to_chapter_start():
    bid, _cid, (a, bb, c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    storage.remove_scene(PROJECT_ID, bid, a)
    entry = next(r["id"] for r in trash.list_scenes(PROJECT_ID, bid) if r["scene_id"] == bb)
    assert trash.restore_scene(PROJECT_ID, bid, entry)["placed"] == "original"
    assert _order(bid) == [[bb, c]]


def test_restore_when_chapter_is_gone_goes_to_end_of_first_chapter():
    bid, _cid, (a, bb, c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    d = storage.story_root(PROJECT_ID) / "trash" / bid / "scenes"
    place = next(d.iterdir()) / "place.json"
    data = json.loads(place.read_text())
    place.write_text(json.dumps({**data, "chapter_id": "f" * 32}))
    out = trash.restore_scene(PROJECT_ID, bid, trash.list_scenes(PROJECT_ID, bid)[0]["id"])
    assert out["placed"] == "end" and _order(bid) == [[a, c, bb]]


def test_old_deletion_without_place_goes_to_end():
    bid, _cid, (a, bb, c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    d = storage.story_root(PROJECT_ID) / "trash" / bid / "scenes"
    (next(d.iterdir()) / "place.json").unlink()                      # Löschung aus 0.6.1–0.15.0
    rows = trash.list_scenes(PROJECT_ID, bid)
    assert rows[0]["title"] == "B" and rows[0]["chapter_exists"] is False and rows[0]["deleted_at"]
    assert trash.restore_scene(PROJECT_ID, bid, rows[0]["id"])["placed"] == "end"
    assert _order(bid) == [[a, c, bb]]


def test_scene_id_in_use_is_409_and_nothing_changes():
    """Zwei Papierkorb-Einträge derselben Szene (z. B. Sicherung kopiert): der zweite überschreibt nie die lebende."""
    import shutil
    bid, _cid, (_a, bb, _c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    entry = trash.list_scenes(PROJECT_ID, bid)[0]["id"]
    d = storage.story_root(PROJECT_ID) / "trash" / bid / "scenes"
    shutil.copytree(d / entry, d / f"{bb}-20200101T000000000000")
    trash.restore_scene(PROJECT_ID, bid, entry)
    before = (storage.get_structure(PROJECT_ID, bid), storage.get_scene(PROJECT_ID, bid, bb))
    with pytest.raises(StoryError) as exc:
        trash.restore_scene(PROJECT_ID, bid, f"{bb}-20200101T000000000000")
    assert exc.value.status == 409 and exc.value.code == "scene_exists"
    assert (storage.get_structure(PROJECT_ID, bid), storage.get_scene(PROJECT_ID, bid, bb)) == before
    assert [r["id"] for r in trash.list_scenes(PROJECT_ID, bid)] == [f"{bb}-20200101T000000000000"]


def test_scene_limit_is_respected(monkeypatch):
    from backend import trash as trash_mod
    bid, _cid, (_a, bb, _c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    monkeypatch.setattr(trash_mod, "MAX_SCENES", 2)
    with pytest.raises(StoryError) as exc:
        trash.restore_scene(PROJECT_ID, bid, trash.list_scenes(PROJECT_ID, bid)[0]["id"])
    assert exc.value.code == "too_many_scenes"
    assert len(trash.list_scenes(PROJECT_ID, bid)) == 1


@pytest.mark.parametrize("bad", ["../x", "a" * 32, f"{'a' * 32}-2026", f"{'a' * 32}-20261008T000000000000/..", ""])
def test_bad_entry_ids_are_404(bad):
    bid, _cid, _ids = _book()
    with pytest.raises(StoryError) as exc:
        trash.restore_scene(PROJECT_ID, bid, bad)
    assert exc.value.status == 404


def test_routes_list_restore_and_rights(client, auth_headers, reader_headers):
    bid, _cid, (_a, bb, _c) = _book()
    storage.remove_scene(PROJECT_ID, bid, bb)
    url = f"{P}/books/{bid}/trash/scenes"
    rows = client.get(url, headers=reader_headers).json()
    assert [r["scene_id"] for r in rows] == [bb]
    assert client.post(f"{url}/{rows[0]['id']}/restore", headers=reader_headers).status_code == 403
    r = client.post(f"{url}/{rows[0]['id']}/restore", headers=auth_headers)
    assert r.status_code == 200 and r.json()["placed"] == "original" and r.json()["scene"]["text"] == "Wichtiger Text von B."
    assert client.get(url, headers=auth_headers).json() == []
