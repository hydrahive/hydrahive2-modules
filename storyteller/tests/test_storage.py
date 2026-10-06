"""Ablage im Projektordner: Pfadschutz, atomares Schreiben, Versionen, Reihenfolge, Papierkorb."""
from __future__ import annotations

import json

import pytest
from conftest import OTHER_PROJECT_ID, PROJECT_ID

from backend import storage
from backend.storage import Conflict, StoryError


def _new(**kw):
    return storage.create_book(PROJECT_ID, {"title": "Der Leuchtturm", "kind": "novel", "language": "de", **kw})


def test_create_book_writes_readable_files():
    b = _new()
    root = storage.book_dir(PROJECT_ID, b["id"])
    assert json.loads((root / "book.json").read_text())["title"] == "Der Leuchtturm"
    st = storage.get_structure(PROJECT_ID, b["id"])
    (scene_id,) = st["parts"][0]["chapters"][0]["scenes"]
    assert (root / "scenes" / f"{scene_id}.md").read_text() == ""
    assert st["parts"][0]["chapters"][0]["title"] == "Kapitel 1"
    assert storage.get_scene(PROJECT_ID, b["id"], scene_id)["title"] == "Szene 1"


def test_sachbuch_und_englisch_bekommen_passende_namen():
    b = _new(kind="nonfiction")
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    assert storage.get_scene(PROJECT_ID, b["id"], sid)["title"] == "Abschnitt 1"
    e = _new(kind="novel", language="en")
    assert storage.get_structure(PROJECT_ID, e["id"])["parts"][0]["title"] == "Part 1"


def test_scene_text_is_plain_markdown_for_agents():
    b = _new()
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "## Nacht\n\nEs **regnete**."}, base_version=1)
    path = storage.book_dir(PROJECT_ID, b["id"]) / "scenes" / f"{sid}.md"
    assert path.read_text() == "## Nacht\n\nEs **regnete**."


@pytest.mark.parametrize("bad", ["../x", "a" * 31, "A" * 32, "../" + "a" * 29, "", "a" * 32 + "/x"])
def test_bad_ids_are_rejected(bad):
    with pytest.raises(StoryError):
        storage.book_dir(PROJECT_ID, bad)
    b = _new()
    with pytest.raises(StoryError):
        storage.get_scene(PROJECT_ID, b["id"], bad)


def test_inside_blocks_paths_leaving_the_base(tmp_path):
    """Zweite Schutzschicht hinter der ID-Prüfung: nichts darf den Buchordner verlassen."""
    from backend._files import inside
    base = tmp_path / "book"
    base.mkdir()
    assert inside(base, "scenes", "x.md") == (base / "scenes" / "x.md").resolve()
    for bad in (("..", "evil"), ("scenes", "..", "..", "evil"), ("/etc/passwd",)):
        with pytest.raises(StoryError):
            inside(base, *bad)


def test_version_conflict_returns_current_state():
    b = _new()
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s1 = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "eins"}, base_version=1)
    assert s1["version"] == 2
    with pytest.raises(Conflict) as exc:
        storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "veraltet"}, base_version=1)
    assert exc.value.current["text"] == "eins" and exc.value.current["version"] == 2
    assert storage.get_scene(PROJECT_ID, b["id"], sid)["text"] == "eins"


def test_structure_version_conflict_and_order_only_in_structure():
    b = _new()
    st = storage.get_structure(PROJECT_ID, b["id"])
    st2 = storage.save_structure(PROJECT_ID, b["id"], {**st, "parts": st["parts"]}, base_version=st["version"])
    with pytest.raises(Conflict):
        storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    meta = json.loads((storage.book_dir(PROJECT_ID, b["id"]) / "scenes" / f"{st['parts'][0]['chapters'][0]['scenes'][0]}.json").read_text())
    assert "position" not in meta and "order" not in meta and st2["version"] == st["version"] + 1


def test_structure_must_reference_existing_scenes_exactly_once():
    b = _new()
    st = storage.get_structure(PROJECT_ID, b["id"])
    sid = st["parts"][0]["chapters"][0]["scenes"][0]
    dup = json.loads(json.dumps(st))
    dup["parts"][0]["chapters"][0]["scenes"] = [sid, sid]
    with pytest.raises(StoryError):
        storage.save_structure(PROJECT_ID, b["id"], dup, base_version=st["version"])
    ghost = json.loads(json.dumps(st))
    ghost["parts"][0]["chapters"][0]["scenes"] = [sid, "b" * 32]
    with pytest.raises(StoryError):
        storage.save_structure(PROJECT_ID, b["id"], ghost, base_version=st["version"])


def test_add_scene_and_remove_scene():
    b = _new()
    st = storage.get_structure(PROJECT_ID, b["id"])
    ch = st["parts"][0]["chapters"][0]["id"]
    r = storage.add_scene(PROJECT_ID, b["id"], ch, title="Szene 2")
    s = r["scene"]
    assert r["structure"] == storage.get_structure(PROJECT_ID, b["id"])
    assert r["structure"]["parts"][0]["chapters"][0]["scenes"][-1] == s["id"]
    st = storage.remove_scene(PROJECT_ID, b["id"], s["id"])
    assert st == storage.get_structure(PROJECT_ID, b["id"])
    assert s["id"] not in st["parts"][0]["chapters"][0]["scenes"]
    assert not (storage.book_dir(PROJECT_ID, b["id"]) / "scenes" / f"{s['id']}.md").exists()


def test_last_scene_of_chapter_cannot_be_removed():
    b = _new()
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    with pytest.raises(StoryError):
        storage.remove_scene(PROJECT_ID, b["id"], sid)


def test_delete_moves_book_to_trash():
    b = _new()
    storage.delete_book(PROJECT_ID, b["id"])
    assert storage.list_books(PROJECT_ID) == []
    trash = list((storage.story_root(PROJECT_ID) / "trash").iterdir())
    assert len(trash) == 1 and (trash[0] / "book.json").exists()


def test_snapshots_are_files_and_capped(monkeypatch):
    from backend import snapshots
    monkeypatch.setattr(snapshots, "MAX_SNAPSHOTS", 3)
    b = _new()
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    v = 1
    for i in range(5):
        v = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": f"Fassung {i}"}, base_version=v)["version"]
        storage.add_snapshot(PROJECT_ID, b["id"], sid)
    snaps = storage.list_snapshots(PROJECT_ID, b["id"], sid)
    assert len(snaps) == 3
    assert snapshots.get_snapshot(PROJECT_ID, b["id"], sid, snaps[0]["id"])["text"] == "Fassung 4"


def test_limits():
    b = _new()
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    with pytest.raises(StoryError):
        storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "x" * (storage.MAX_SCENE_BYTES + 1)}, base_version=1)
    with pytest.raises(StoryError):
        storage.create_book(PROJECT_ID, {"title": "", "kind": "novel", "language": "de"})
    with pytest.raises(StoryError):
        storage.create_book(PROJECT_ID, {"title": "X", "kind": "comic", "language": "de"})


def test_projects_are_separate():
    b = _new()
    assert [x["id"] for x in storage.list_books(PROJECT_ID)] == [b["id"]]
    assert storage.list_books(OTHER_PROJECT_ID) == []
    with pytest.raises(StoryError):
        storage.get_book(OTHER_PROJECT_ID, b["id"])


def test_write_is_atomic(monkeypatch):
    """Bricht das Schreiben ab, bleibt die alte Datei unversehrt und es bleibt kein Rest liegen."""
    b = _new()
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "sicher"}, base_version=1)
    import os

    def boom(*a, **k):
        raise OSError("Platte voll")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "kaputt"}, base_version=2)
    monkeypatch.undo()
    assert storage.get_scene(PROJECT_ID, b["id"], sid)["text"] == "sicher"
    leftovers = [p.name for p in (storage.book_dir(PROJECT_ID, b["id"]) / "scenes").iterdir() if p.name.startswith(".")]
    assert leftovers == []


@pytest.mark.parametrize("pid", ["..", "../x", "a/b", "kurz", "x" * 65, "abc def ghi", ""])
def test_project_id_with_path_characters_never_reaches_the_filesystem(pid, monkeypatch):
    """Projekt-ID wird geprüft, bevor überhaupt ein Workspace-Pfad gebaut wird."""
    import backend._files as files

    def must_not_be_called(_):
        raise AssertionError("ensure_workspace darf mit ungültiger ID nicht aufgerufen werden")
    monkeypatch.setattr(files, "ensure_workspace", must_not_be_called)
    with pytest.raises(StoryError) as exc:
        storage.story_root(pid)
    assert exc.value.status == 404
