"""Routen für Projekt am Board, Vorschlag übernehmen und verwerfen, frühere Fassungen (Etappe 3a)."""
from __future__ import annotations

import json

from backend import proposals
from conftest import PROJECT_A, PROJECT_B

BASE = "/api/modules/blueprint/boards"


def _h(client, user="testuser"):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def graph(count: int, tag: str = "n") -> dict:
    return {"nodes": [{"id": f"{tag}{i}", "type": "flowNode", "position": {"x": 0, "y": 0},
                       "data": {"kind": "flow", "subtype": "action", "label": f"{tag}{i}", "note": ""}}
                      for i in range(count)], "edges": []}


def ids(graph_json: str) -> list[str]:
    return [node["id"] for node in json.loads(graph_json)["nodes"]]


def _board(client, headers, count: int = 2, **body) -> int:
    r = client.post(BASE, json={"name": "Board", **body}, headers=headers)
    assert r.status_code == 201, r.text
    bid = r.json()["id"]
    if count:
        r = client.put(f"{BASE}/{bid}", json={"graph_json": json.dumps(graph(count, "alt"))}, headers=headers)
        assert r.status_code == 200, r.text
    return bid


def _code(response) -> str:
    return response.json()["detail"]["code"]


def test_board_mit_projekt_anlegen_und_liste_filtern(client, auth_headers):
    with_project = _board(client, auth_headers, 0, project_id=PROJECT_A)
    without = _board(client, auth_headers, 0)
    assert client.get(f"{BASE}/{with_project}", headers=auth_headers).json()["project_id"] == PROJECT_A
    everything = client.get(BASE, headers=auth_headers).json()
    assert {b["id"] for b in everything} == {with_project, without}
    filtered = client.get(BASE, params={"project_id": PROJECT_A}, headers=auth_headers).json()
    assert [b["id"] for b in filtered] == [with_project]


def test_fremdes_und_unbekanntes_projekt_sehen_gleich_aus(client, auth_headers):
    for project in (PROJECT_B, "gibt-es-nicht-projekt", "../../etc"):
        r = client.post(BASE, json={"name": "Board", "project_id": project}, headers=auth_headers)
        assert r.status_code == 404 and _code(r) == "project_not_found", project
    bid = _board(client, auth_headers, 0)
    r = client.put(f"{BASE}/{bid}", json={"project_id": PROJECT_B}, headers=auth_headers)
    assert r.status_code == 404 and _code(r) == "project_not_found"
    assert client.get(BASE, headers=auth_headers).json()[0]["project_id"] is None


def test_projekt_am_board_aendern_und_entfernen(client, auth_headers):
    bid = _board(client, auth_headers, 0)
    assert client.put(f"{BASE}/{bid}", json={"project_id": PROJECT_A}, headers=auth_headers).json()["project_id"] == PROJECT_A
    # Ohne Angabe bleibt das Projekt stehen, mit null wird es entfernt.
    assert client.put(f"{BASE}/{bid}", json={"name": "Neu"}, headers=auth_headers).json()["project_id"] == PROJECT_A
    assert client.put(f"{BASE}/{bid}", json={"project_id": None}, headers=auth_headers).json()["project_id"] is None


def test_board_zeigt_den_offenen_vorschlag(client, auth_headers):
    bid = _board(client, auth_headers)
    proposals.put("testuser", bid, graph(3, "neu"), "mit Fehlerfall")
    board = client.get(f"{BASE}/{bid}", headers=auth_headers).json()
    assert ids(board["proposal_json"]) == ["neu0", "neu1", "neu2"]
    assert board["proposal_note"] == "mit Fehlerfall" and board["proposal_at"]
    assert client.get(BASE, headers=auth_headers).json()[0]["has_proposal"] is True


def test_vorschlag_uebernehmen(client, auth_headers):
    bid = _board(client, auth_headers)
    proposals.put("testuser", bid, graph(3, "neu"), "")
    r = client.post(f"{BASE}/{bid}/proposal/accept", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert ids(r.json()["graph_json"]) == ["neu0", "neu1", "neu2"] and r.json()["proposal_json"] is None
    listed = client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json()
    assert [(v["source"], v["node_count"]) for v in listed] == [("proposal", 2)]


def test_uebernehmen_ohne_vorschlag_ist_ein_konflikt(client, auth_headers):
    bid = _board(client, auth_headers)
    r = client.post(f"{BASE}/{bid}/proposal/accept", headers=auth_headers)
    assert r.status_code == 409 and _code(r) == "no_proposal"


def test_vorschlag_verwerfen(client, auth_headers):
    bid = _board(client, auth_headers)
    proposals.put("testuser", bid, graph(3, "neu"), "")
    r = client.delete(f"{BASE}/{bid}/proposal", headers=auth_headers)
    assert r.status_code == 200 and r.json()["proposal_json"] is None
    assert ids(r.json()["graph_json"]) == ["alt0", "alt1"]
    assert client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json() == []


def test_fassung_wiederherstellen(client, auth_headers):
    bid = _board(client, auth_headers)
    proposals.put("testuser", bid, graph(3, "neu"), "")
    client.post(f"{BASE}/{bid}/proposal/accept", headers=auth_headers)
    version_id = client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json()[0]["id"]
    r = client.post(f"{BASE}/{bid}/versions/{version_id}/restore", headers=auth_headers)
    assert r.status_code == 200 and ids(r.json()["graph_json"]) == ["alt0", "alt1"]
    r = client.post(f"{BASE}/{bid}/versions/999999/restore", headers=auth_headers)
    assert r.status_code == 404 and _code(r) == "version_not_found"


def test_fremdes_board_bleibt_unsichtbar(client, auth_headers):
    bid = _board(client, auth_headers)
    proposals.put("testuser", bid, graph(3, "neu"), "")
    other = _h(client, "other")
    for response in (
        client.post(f"{BASE}/{bid}/proposal/accept", headers=other),
        client.delete(f"{BASE}/{bid}/proposal", headers=other),
        client.get(f"{BASE}/{bid}/versions", headers=other),
        client.post(f"{BASE}/{bid}/versions/1/restore", headers=other),
    ):
        assert response.status_code == 404 and _code(response) == "board_not_found"
    assert client.get(f"{BASE}/{bid}", headers=auth_headers).json()["proposal_json"] is not None


def test_neue_routen_brauchen_eine_anmeldung(client):
    assert client.post(f"{BASE}/1/proposal/accept").status_code in (401, 403)
    assert client.delete(f"{BASE}/1/proposal").status_code in (401, 403)
    assert client.get(f"{BASE}/1/versions").status_code in (401, 403)
    assert client.post(f"{BASE}/1/versions/1/restore").status_code in (401, 403)


def test_vorschlag_laesst_sich_ueber_die_routen_nicht_einschleusen(client, auth_headers):
    bid = _board(client, auth_headers)
    r = client.put(f"{BASE}/{bid}", json={"proposal_json": json.dumps(graph(1)), "proposal_note": "x"}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["proposal_json"] is None and r.json()["proposal_note"] is None
