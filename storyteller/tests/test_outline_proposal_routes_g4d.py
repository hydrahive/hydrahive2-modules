"""Ghostwriter G4d: Routen für den Gliederungs-Vorschlag."""
from __future__ import annotations

from backend import proposals_outline as po
from backend import storage
from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"
OUT = {"chapters": [{"title": "Sturm", "scenes": [{"title": "Die Nacht", "summary": "Ein Sturm zieht auf."}]}]}


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    po.store(PROJECT_ID, b["id"], OUT, session_id="s")
    return b["id"], storage.get_structure(PROJECT_ID, b["id"])


def test_get_open_book_accept_edited(client, auth_headers):
    bid, st = _book()
    url = f"{P}/books/{bid}/proposals/outline"
    assert client.get(url, headers=auth_headers).json()["outline"]["chapters"][0]["title"] == "Sturm"
    assert client.get(f"{P}/books/{bid}", headers=auth_headers).json()["outline_proposal"]["source"] == "agent"
    edited = {"chapters": [{"title": "Sturm (neu)", "scenes": [{"title": "Die Nacht", "summary": "Bearbeitet."}]}]}
    r = client.post(f"{url}/accept", json={"outline": edited, "base_version": st["version"] - 1}, headers=auth_headers)
    assert r.status_code == 409
    r = client.post(f"{url}/accept", json={"outline": edited, "base_version": st["version"]}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["structure"]["parts"][0]["chapters"][0]["title"] == "Sturm (neu)"
    assert client.get(url, headers=auth_headers).status_code == 404
    assert client.get(f"{P}/books/{bid}", headers=auth_headers).json()["outline_proposal"] is None


def test_discard_reader_foreign(client, auth_headers, reader_headers, other_headers):
    bid, st = _book()
    url = f"{P}/books/{bid}/proposals/outline"
    assert client.get(url, headers=reader_headers).status_code == 200
    assert client.post(f"{url}/accept", json={"outline": OUT, "base_version": st["version"]}, headers=reader_headers).status_code == 403
    assert client.delete(url, headers=reader_headers).status_code == 403
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.delete(url, headers=auth_headers).status_code == 200
    assert client.get(url, headers=auth_headers).status_code == 404


def test_outline_path_is_not_read_as_scene_id(client, auth_headers):
    bid, _ = _book()
    r = client.get(f"{P}/books/{bid}/proposals/outline", headers=auth_headers)
    assert r.status_code == 200 and "outline" in r.json()
