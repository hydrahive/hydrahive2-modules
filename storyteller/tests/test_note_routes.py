"""T1d: Routen für Hinweise/Notizen (lesen: Projektmitglied; abhaken/löschen: Schreibrecht)."""
from __future__ import annotations

from backend import storage, team_notes
from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _book_with_notes():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    a = team_notes.add(PROJECT_ID, b["id"], {"kind": "hint", "title": "A", "text": "a", "scene_id": sid, "author": "P"})
    n = team_notes.add(PROJECT_ID, b["id"], {"kind": "note", "title": "B", "text": "b", "author": "R",
                                             "sources": [{"url": "https://example.org"}]})
    return b["id"], sid, a, n


def test_list_open_and_all_and_by_scene(client, reader_headers):
    bid, sid, a, n = _book_with_notes()  # noqa: RUF059
    r = client.get(f"{P}/books/{bid}/notes", headers=reader_headers)
    assert r.status_code == 200 and [x["title"] for x in r.json()] == ["A", "B"]
    assert [x["title"] for x in client.get(f"{P}/books/{bid}/notes?scene_id={sid}", headers=reader_headers).json()] == ["A"]
    team_notes.set_status(PROJECT_ID, bid, a["id"], "done")
    assert [x["title"] for x in client.get(f"{P}/books/{bid}/notes", headers=reader_headers).json()] == ["B"]
    assert len(client.get(f"{P}/books/{bid}/notes?status=all", headers=reader_headers).json()) == 2


def test_set_status_and_delete_need_write(client, auth_headers, reader_headers):
    bid, sid, a, n = _book_with_notes()  # noqa: RUF059
    assert client.patch(f"{P}/books/{bid}/notes/{a['id']}", json={"status": "done"}, headers=reader_headers).status_code == 403
    assert client.delete(f"{P}/books/{bid}/notes/{a['id']}", headers=reader_headers).status_code == 403
    r = client.patch(f"{P}/books/{bid}/notes/{a['id']}", json={"status": "done"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "done"
    bad = client.patch(f"{P}/books/{bid}/notes/{a['id']}", json={"status": "egal"}, headers=auth_headers)
    assert bad.status_code == 422
    assert client.delete(f"{P}/books/{bid}/notes/{n['id']}", headers=auth_headers).status_code == 200
    assert client.delete(f"{P}/books/{bid}/notes/{n['id']}", headers=auth_headers).status_code == 404


def test_open_book_reports_open_notes_per_scene(client, auth_headers):
    bid, sid, a, n = _book_with_notes()  # noqa: RUF059
    assert client.get(f"{P}/books/{bid}", headers=auth_headers).json()["open_notes"] == {sid: 1}


def test_foreign_user_sees_nothing(client, other_headers):
    bid, sid, a, n = _book_with_notes()  # noqa: RUF059
    assert client.get(f"{P}/books/{bid}/notes", headers=other_headers).status_code == 404
    assert client.patch(f"{P}/books/{bid}/notes/{a['id']}", json={"status": "done"}, headers=other_headers).status_code == 404
