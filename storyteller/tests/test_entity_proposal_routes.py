"""Ghostwriter G4c: Routen für Steckbrief-Vorschläge."""
from __future__ import annotations

from backend import proposals_entities as pe
from backend import storage
from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"
MIA = "e" * 32


def _book():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    st = storage.get_structure(PROJECT_ID, b["id"])
    st["entities"] = [{"id": MIA, "kind": "character", "name": "Mia", "aliases": [], "description": "Zwölf.", "fields": []}]
    st = storage.save_structure(PROJECT_ID, b["id"], st, base_version=st["version"])
    new = pe.store(PROJECT_ID, b["id"], None, {"kind": "place", "name": "Leuchtturm"}, session_id="s")
    change = pe.store(PROJECT_ID, b["id"], MIA, {"description": "Mutig."})
    return b["id"], st, new, change


def test_open_book_and_list_include_entity_proposals(client, auth_headers):
    bid, _, new, change = _book()
    full = client.get(f"{P}/books/{bid}", headers=auth_headers).json()
    assert {p["id"] for p in full["entity_proposals"]} == {new["id"], change["id"]}
    lst = client.get(f"{P}/books/{bid}/proposals/entities", headers=auth_headers).json()
    assert [p["id"] for p in lst] == [new["id"], change["id"]]


def test_accept_returns_structure_and_conflict(client, auth_headers):
    bid, st, new, change = _book()
    url = f"{P}/books/{bid}/proposals/entities"
    r = client.post(f"{url}/{new['id']}/accept", json={"base_version": st["version"] - 1}, headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "version_conflict"
    r = client.post(f"{url}/{new['id']}/accept", json={"base_version": st["version"]}, headers=auth_headers)
    assert r.status_code == 200 and any(e["name"] == "Leuchtturm" for e in r.json()["entities"])
    v = r.json()["version"]
    r = client.post(f"{url}/{change['id']}/accept", json={"base_version": v}, headers=auth_headers)
    assert r.status_code == 200 and next(e for e in r.json()["entities"] if e["id"] == MIA)["description"] == "Mutig."
    assert client.get(url, headers=auth_headers).json() == []


def test_discard_reader_foreign_and_unknown(client, auth_headers, reader_headers, other_headers):
    bid, st, new, _ = _book()
    url = f"{P}/books/{bid}/proposals/entities"
    assert client.get(url, headers=reader_headers).status_code == 200
    assert client.post(f"{url}/{new['id']}/accept", json={"base_version": st["version"]}, headers=reader_headers).status_code == 403
    assert client.delete(f"{url}/{new['id']}", headers=reader_headers).status_code == 403
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.post(f"{url}/{'f' * 32}/accept", json={"base_version": st["version"]}, headers=auth_headers).status_code == 404
    assert client.delete(f"{url}/{new['id']}", headers=auth_headers).status_code == 200
    assert [p["id"] for p in client.get(url, headers=auth_headers).json()] != [new["id"]]


def test_entities_path_is_not_read_as_scene_id(client, auth_headers):
    """…/proposals/entities muss vor …/proposals/{scene_id} greifen."""
    bid, *_ = _book()
    r = client.get(f"{P}/books/{bid}/proposals/entities", headers=auth_headers)
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_exists_error_carries_entity_id(client, auth_headers):
    """Die Zusatzangabe (vorhandene ID) kommt als params in der Antwort an – Grundlage für Oberfläche/Agent."""
    import pytest
    from backend._route_base import _call
    from fastapi import HTTPException
    bid, *_ = _book()
    with pytest.raises(HTTPException) as exc:
        _call(pe.store, PROJECT_ID, bid, None, {"kind": "character", "name": "Mia"})
    assert exc.value.status_code == 409 and exc.value.detail == {"code": "entity_exists", "params": {"entity_id": MIA, "name": "Mia"}}
