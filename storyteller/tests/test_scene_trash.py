"""Szene löschen verschiebt in den Papierkorb statt endgültig zu löschen (Fix 0.6.1, Task af55e68c)."""
from __future__ import annotations

from conftest import PROJECT_ID

from backend import outline, proposals, snapshots, storage


def _book_with_scene():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    sid = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "Weg")["scene"]["id"]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Wichtiger Text", "summary": "Z"}, base_version=1)
    snapshots.add_snapshot(PROJECT_ID, b["id"], sid, "Ältere Fassung")
    proposals.store(PROJECT_ID, b["id"], sid, "Vorschlag", run_id="r", model="m", base_version=s["version"])
    return b["id"], sid


def _trash(bid):
    return storage.story_root(PROJECT_ID) / "trash" / bid / "scenes"


def test_remove_scene_moves_text_infos_snapshots_and_proposal_to_trash():
    bid, sid = _book_with_scene()
    storage.remove_scene(PROJECT_ID, bid, sid)
    d = storage.book_dir(PROJECT_ID, bid)
    assert not any(sid in str(p) for p in d.rglob("*"))                      # nichts mehr im Buch
    found = [p for p in _trash(bid).iterdir() if p.name.startswith(sid)]
    assert len(found) == 1
    t = found[0]
    assert (t / f"{sid}.md").read_text(encoding="utf-8") == "Wichtiger Text"
    assert (t / f"{sid}.json").is_file()
    assert [p.read_text(encoding="utf-8") for p in (t / "snapshots").glob("*.md")] == ["Ältere Fassung"]
    assert (t / "proposal.md").read_text(encoding="utf-8") == "Vorschlag" and (t / "proposal.json").is_file()
    assert proposals.list_for_book(PROJECT_ID, bid) == []


def test_remove_scene_without_extras_and_twice():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    ch = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]
    a = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "A")["scene"]["id"]
    c = storage.add_scene(PROJECT_ID, b["id"], ch["id"], "C")["scene"]["id"]
    storage.remove_scene(PROJECT_ID, b["id"], a)
    storage.remove_scene(PROJECT_ID, b["id"], c)
    names = sorted(p.name[:32] for p in _trash(b["id"]).iterdir())
    assert names == sorted([a, c])


def test_outline_apply_moves_replaced_placeholder_scene_to_trash():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    lone = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    st = storage.get_structure(PROJECT_ID, b["id"])
    outline.apply(PROJECT_ID, b["id"], {"chapters": [{"title": "K", "scenes": [{"title": "S", "summary": "x"}]}],
                                         "entities": []}, base_version=st["version"])
    assert not (storage.book_dir(PROJECT_ID, b["id"]) / "scenes" / f"{lone}.json").exists()
    assert any(p.name.startswith(lone) for p in _trash(b["id"]).iterdir())


def test_route_delete_scene_still_works(client, auth_headers):
    from conftest import MOD_PREFIX
    bid, sid = _book_with_scene()
    r = client.delete(f"{MOD_PREFIX}/projects/{PROJECT_ID}/books/{bid}/scenes/{sid}", headers=auth_headers)
    assert r.status_code == 200 and sid not in str(r.json())
    assert any(p.name.startswith(sid) for p in _trash(bid).iterdir())
