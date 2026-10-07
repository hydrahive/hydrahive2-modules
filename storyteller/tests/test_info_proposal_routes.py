"""Ghostwriter G4b: Routen für Vorschläge zu Szenen-Infos (ansehen, übernehmen, verwerfen, beim Öffnen/Nachfragen)."""
from __future__ import annotations

from backend import proposals_info, storage
from conftest import MOD_PREFIX, PROJECT_ID

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"


def _scene():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"title": "Alt", "summary": "Alt."}, base_version=1)
    proposals_info.store(PROJECT_ID, b["id"], sid, {"title": "Neu", "summary": "Neu."}, base_version=s["version"],
                         source="agent", session_id="s1", note="N")
    return b["id"], sid, s


def test_open_book_and_proposal_list_include_info(client, auth_headers):
    bid, sid, _ = _scene()
    full = client.get(f"{P}/books/{bid}", headers=auth_headers).json()
    assert full["info_proposals"][0]["scene_id"] == sid and full["info_proposals"][0]["fields"]["title"] == "Neu"
    lst = client.get(f"{P}/books/{bid}/proposals", headers=auth_headers).json()
    assert lst == []                                                    # Text-Vorschläge: keine
    infos = client.get(f"{P}/books/{bid}/proposals/info", headers=auth_headers).json()
    assert infos[0]["scene_id"] == sid and infos[0]["note"] == "N"


def test_accept_selected_fields_and_conflict(client, auth_headers):
    bid, sid, s = _scene()
    url = f"{P}/books/{bid}/proposals/{sid}/info/accept"
    r = client.post(url, json={"base_version": s["version"] - 1}, headers=auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "version_conflict"
    r = client.post(url, json={"base_version": s["version"], "fields": ["title"]}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["title"] == "Neu" and r.json()["summary"] == "Alt."
    assert client.post(url, json={"base_version": s["version"] + 1}, headers=auth_headers).status_code == 404


def test_bad_fields_and_discard(client, auth_headers):
    bid, sid, s = _scene()
    url = f"{P}/books/{bid}/proposals/{sid}/info"
    r = client.post(f"{url}/accept", json={"base_version": s["version"], "fields": ["text"]}, headers=auth_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "fields_invalid"
    assert client.delete(url, headers=auth_headers).status_code == 200
    assert client.get(f"{P}/books/{bid}/proposals/info", headers=auth_headers).json() == []


def test_reader_and_foreign(client, reader_headers, other_headers):
    bid, sid, s = _scene()
    url = f"{P}/books/{bid}/proposals/{sid}/info"
    assert client.get(f"{P}/books/{bid}/proposals/info", headers=reader_headers).status_code == 200
    assert client.post(f"{url}/accept", json={"base_version": s["version"]}, headers=reader_headers).status_code == 403
    assert client.delete(url, headers=reader_headers).status_code == 403
    assert client.get(f"{P}/books/{bid}/proposals/info", headers=other_headers).status_code == 404
    assert client.post(f"{url}/accept", json={"base_version": s["version"]}, headers=other_headers).status_code == 404
    assert proposals_info.get(PROJECT_ID, bid, sid)["fields"]["title"] == "Neu"


def test_info_list_is_not_read_as_scene_id_and_text_proposal_routes_still_work(client, auth_headers):
    """…/proposals/info muss vor …/proposals/{scene_id} greifen; Text-Vorschlag bleibt unter der Szenen-ID erreichbar."""
    from backend import proposals
    bid, sid, s = _scene()
    proposals.store(PROJECT_ID, bid, sid, "Text-Vorschlag", run_id="", model="", base_version=s["version"])
    r = client.get(f"{P}/books/{bid}/proposals/info", headers=auth_headers)
    assert r.status_code == 200 and isinstance(r.json(), list)
    assert client.get(f"{P}/books/{bid}/proposals/{sid}", headers=auth_headers).json()["text"] == "Text-Vorschlag"
