"""A2: Routen für den Vorschlags-Verlauf – Liste je Szene, Ansehen, Zurückholen; Rechte und IDs."""
from __future__ import annotations

from conftest import MOD_PREFIX, OTHER_PROJECT_ID, PROJECT_ID

from backend import proposals, proposals_info, proposals_outline, storage

P = f"{MOD_PREFIX}/projects/{PROJECT_ID}"
OUT = {"chapters": [{"title": "Ankunft", "scenes": [{"title": "Die Fähre", "summary": "Mia kommt an."}]}]}


def _scene():
    b = storage.create_book(PROJECT_ID, {"title": "T", "kind": "novel", "language": "de"})
    sid = storage.get_structure(PROJECT_ID, b["id"])["parts"][0]["chapters"][0]["scenes"][0]
    s = storage.save_scene(PROJECT_ID, b["id"], sid, {"text": "Text.", "title": "Alt"}, base_version=1)
    return b["id"], sid, s


def _two_text(bid, sid, s):
    proposals.store(PROJECT_ID, bid, sid, "Fassung Lauf.", run_id="r1", model="m", base_version=s["version"])
    proposals.store(PROJECT_ID, bid, sid, "Fassung Lektor.", run_id="", model="", base_version=s["version"],
                    source="agent", author="T — Lektor")


def test_list_contains_text_and_info_newest_first_without_text(client, reader_headers):
    bid, sid, s = _scene()
    _two_text(bid, sid, s)
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    proposals_info.discard(PROJECT_ID, bid, sid)
    r = client.get(f"{P}/books/{bid}/scenes/{sid}/proposal-history", headers=reader_headers)
    assert r.status_code == 200
    rows = r.json()
    assert [(x["kind"], x["reason"]) for x in rows] == [("info", "discarded"), ("text", "replaced")]
    assert rows[1]["author"] == "Ghostwriter-Lauf" and rows[1]["replaced_by"] == "T — Lektor" and "text" not in rows[1]


def test_view_and_restore(client, auth_headers):
    bid, sid, s = _scene()
    _two_text(bid, sid, s)
    url = f"{P}/books/{bid}/scenes/{sid}/proposal-history"
    eid = client.get(url, headers=auth_headers).json()[0]["id"]
    one = client.get(f"{url}/text/{eid}", headers=auth_headers).json()
    assert one["text"] == "Fassung Lauf." and one["words"] == 2
    r = client.post(f"{url}/text/{eid}/restore", headers=auth_headers)
    assert r.status_code == 200 and r.json()["text"] == "Fassung Lauf."
    assert proposals.get(PROJECT_ID, bid, sid)["text"] == "Fassung Lauf."
    rows = client.get(url, headers=auth_headers).json()
    assert len(rows) == 1 and rows[0]["replaced_by"] == "zurückgeholt"


def test_restore_info_route(client, auth_headers):
    bid, sid, s = _scene()
    proposals_info.store(PROJECT_ID, bid, sid, {"title": "Neu"}, base_version=s["version"])
    proposals_info.discard(PROJECT_ID, bid, sid)
    url = f"{P}/books/{bid}/scenes/{sid}/proposal-history"
    eid = client.get(url, headers=auth_headers).json()[0]["id"]
    r = client.post(f"{url}/info/{eid}/restore", headers=auth_headers)
    assert r.status_code == 200 and r.json()["fields"] == {"title": "Neu"}


def test_outline_and_entity_history_routes(client, auth_headers):
    bid, _sid, _s = _scene()
    proposals_outline.store(PROJECT_ID, bid, OUT)
    proposals_outline.discard(PROJECT_ID, bid)
    rows = client.get(f"{P}/books/{bid}/proposal-history/outline", headers=auth_headers).json()
    assert len(rows) == 1 and rows[0]["chapters"] == 1
    r = client.post(f"{P}/books/{bid}/proposal-history/outline/{rows[0]['id']}/restore", headers=auth_headers)
    assert r.status_code == 200 and proposals_outline.get(PROJECT_ID, bid)
    assert client.get(f"{P}/books/{bid}/proposal-history/entity/new", headers=auth_headers).json() == []


def test_rights_reader_cannot_restore_foreign_404(client, auth_headers, reader_headers, other_headers):
    bid, sid, s = _scene()
    _two_text(bid, sid, s)
    url = f"{P}/books/{bid}/scenes/{sid}/proposal-history"
    eid = client.get(url, headers=auth_headers).json()[0]["id"]
    assert client.post(f"{url}/text/{eid}/restore", headers=reader_headers).status_code == 403
    assert client.get(url, headers=other_headers).status_code in (403, 404)
    other = f"{MOD_PREFIX}/projects/{OTHER_PROJECT_ID}/books/{bid}/scenes/{sid}/proposal-history"
    assert client.get(other, headers=other_headers).status_code == 404


def test_bad_ids_and_kinds(client, auth_headers):
    bid, sid, _s = _scene()
    url = f"{P}/books/{bid}/scenes/{sid}/proposal-history"
    assert client.get(f"{url}/text/..%2F..%2Fbook", headers=auth_headers).status_code == 404
    assert client.get(f"{url}/text/20261008T000000000000", headers=auth_headers).status_code == 404
    assert client.get(f"{url}/outline/20261008T000000000000", headers=auth_headers).status_code in (400, 404, 422)
    assert client.get(f"{P}/books/{bid}/scenes/{'0' * 32}/proposal-history", headers=auth_headers).status_code == 404
