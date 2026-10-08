"""A3: gelöschte Bücher wiederherstellen; Umzugs-Sicherungen nur anzeigen (Spec nichts-geht-verloren.md §3)."""
from __future__ import annotations

import shutil

import pytest
from conftest import MOD_PREFIX, PROJECT_ID

from backend import storage, trash_books
from backend._files import StoryError

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book(title="Der Leuchtturm"):
    b = storage.create_book(PROJECT_ID, {"title": title, "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Drei Wörter hier."}, base_version=1)
    return b["id"], sid


def _mine(rows, bid):
    return [r for r in rows if r["book_id"] == bid]


def test_deleted_book_is_listed_and_restored_with_everything():
    bid, sid = _book()
    storage.delete_book(PROJECT_ID, bid)
    assert bid not in [b["id"] for b in storage.list_books(PROJECT_ID)]
    rows = _mine(trash_books.list_books(PROJECT_ID), bid)
    assert len(rows) == 1
    r = rows[0]
    assert r["kind"] == "deleted" and r["title"] == "Der Leuchtturm" and r["scenes"] == 1 and r["words"] == 3
    assert r["deleted_at"] and r["restorable"] is True
    out = trash_books.restore_book(PROJECT_ID, r["id"])
    assert out["id"] == bid and out["title"] == "Der Leuchtturm"
    assert storage.get_scene(PROJECT_ID, bid, sid)["text"] == "Drei Wörter hier."
    assert _mine(trash_books.list_books(PROJECT_ID), bid) == []


def test_restore_when_book_id_is_back_already_is_409():
    bid, _sid = _book()
    storage.delete_book(PROJECT_ID, bid)
    entry = _mine(trash_books.list_books(PROJECT_ID), bid)[0]["id"]
    trash_dir = storage.story_root(PROJECT_ID) / "trash"
    shutil.copytree(trash_dir / entry, trash_dir / f"{bid}-20200101T000000000000")   # zweite Kopie desselben Buchs
    trash_books.restore_book(PROJECT_ID, entry)
    with pytest.raises(StoryError) as exc:
        trash_books.restore_book(PROJECT_ID, f"{bid}-20200101T000000000000")
    assert exc.value.status == 409 and exc.value.code == "book_exists"


def test_moved_backup_is_shown_but_not_restorable():
    bid, _sid = _book("Umgezogen")
    src = storage.book_dir(PROJECT_ID, bid)
    backup = storage.story_root(PROJECT_ID) / "trash" / "moved" / f"{bid}-20261008T204840"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(backup))
    rows = _mine(trash_books.list_books(PROJECT_ID), bid)
    assert len(rows) == 1 and rows[0]["kind"] == "moved" and rows[0]["restorable"] is False and rows[0]["title"] == "Umgezogen"
    with pytest.raises(StoryError) as exc:
        trash_books.restore_book(PROJECT_ID, rows[0]["id"])
    assert exc.value.code == "trash_entry_not_found"


def test_scene_trash_folder_of_a_live_book_is_not_a_deleted_book():
    """trash/<buch>/scenes/ (gelöschte Szenen) ist kein gelöschtes Buch."""
    bid, _sid = _book()
    ch = storage.get_structure(PROJECT_ID, bid)["parts"][0]["chapters"][0]
    extra = storage.add_scene(PROJECT_ID, bid, ch["id"], "X")["scene"]["id"]
    storage.remove_scene(PROJECT_ID, bid, extra)
    assert _mine(trash_books.list_books(PROJECT_ID), bid) == []


@pytest.mark.parametrize("bad", ["../books", "moved", f"{'a' * 32}", f"{'a' * 32}-20261008T000000000000"])
def test_bad_entries_are_404(bad):
    with pytest.raises(StoryError) as exc:
        trash_books.restore_book(PROJECT_ID, bad)
    assert exc.value.status == 404


def test_routes_and_rights(client, auth_headers, reader_headers):
    bid, _sid = _book("Routenbuch")
    storage.delete_book(PROJECT_ID, bid)
    rows = _mine(client.get(f"{P}/trash/books", headers=reader_headers).json(), bid)
    assert len(rows) == 1
    url = f"{P}/trash/books/{rows[0]['id']}/restore"
    assert client.post(url, headers=reader_headers).status_code == 403
    r = client.post(url, headers=auth_headers)
    assert r.status_code == 200 and r.json()["id"] == bid
    assert bid in [b["id"] for b in client.get(f"{P}/books", headers=auth_headers).json()]
