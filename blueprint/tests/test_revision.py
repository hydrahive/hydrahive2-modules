"""Fassungszähler am Board: Eine offene Zeichenfläche überschreibt nichts, was sie nicht kennt (Etappe 3a).

Die Zeichenfläche speichert selbsttätig. Zeichnet der Agent inzwischen direkt auf ein leeres Board
oder wird ein Vorschlag in einem anderen Fenster übernommen, darf das nächste Speichern der alten
Ansicht diese Fassung nicht ersetzen.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend import proposals

BASE = "/api/modules/blueprint/boards"
MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def graph(count: int, tag: str = "n") -> dict:
    return {"nodes": [{"id": f"{tag}{i}", "type": "flowNode", "position": {"x": 0, "y": 0},
                       "data": {"kind": "flow", "subtype": "action", "label": f"{tag}{i}", "note": ""}}
                      for i in range(count)], "edges": []}


def ids(graph_json: str) -> list[str]:
    return [node["id"] for node in json.loads(graph_json)["nodes"]]


def _h(client, user="other"):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _new(client, headers) -> dict:
    r = client.post(BASE, json={"name": "Board"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def _save(client, headers, bid: int, count: int, tag: str, **extra):
    return client.put(f"{BASE}/{bid}", json={"graph_json": json.dumps(graph(count, tag)), **extra}, headers=headers)


def _code(response) -> str:
    return response.json()["detail"]["code"]


def test_zaehler_steigt_nur_wenn_sich_die_fassung_aendert(client, auth_headers):
    board = _new(client, auth_headers)
    assert board["revision"] == 0
    assert _save(client, auth_headers, board["id"], 1, "a").json()["revision"] == 1
    renamed = client.put(f"{BASE}/{board['id']}", json={"name": "Anders"}, headers=auth_headers).json()
    assert renamed["revision"] == 1
    assert _save(client, auth_headers, board["id"], 2, "b").json()["revision"] == 2


def test_speichern_mit_passendem_stand_geht_durch(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    first = _save(client, auth_headers, bid, 1, "a", base_revision=0)
    assert first.status_code == 200 and first.json()["revision"] == 1
    second = _save(client, auth_headers, bid, 2, "b", base_revision=1)
    assert second.status_code == 200 and ids(second.json()["graph_json"]) == ["b0", "b1"]


def test_speichern_mit_veraltetem_stand_wird_abgelehnt(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    _save(client, auth_headers, bid, 2, "anderes-fenster", base_revision=0)
    late = _save(client, auth_headers, bid, 1, "alt", base_revision=0)
    assert late.status_code == 409 and _code(late) == "board_changed"
    stored = client.get(f"{BASE}/{bid}", headers=auth_headers).json()
    assert ids(stored["graph_json"]) == ["anderes-fenster0", "anderes-fenster1"] and stored["revision"] == 1


def test_offene_zeichenflaeche_ueberschreibt_den_entwurf_des_agenten_nicht(client, auth_headers):
    """Der Fund aus useBoard.ts: Das Board ist offen und leer, der Agent zeichnet direkt, dann speichert die Ansicht."""
    board = _new(client, auth_headers)
    drawn = proposals.put("testuser", board["id"], graph(3, "agent"), "erster Entwurf")
    assert drawn["drawn"] is True and drawn["board"]["revision"] == 1
    late = _save(client, auth_headers, board["id"], 1, "nutzer", base_revision=board["revision"])
    assert late.status_code == 409 and _code(late) == "board_changed"
    stored = client.get(f"{BASE}/{board['id']}", headers=auth_headers).json()
    assert ids(stored["graph_json"]) == ["agent0", "agent1", "agent2"]


def test_vorschlag_daneben_aendert_den_zaehler_nicht(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    _save(client, auth_headers, bid, 2, "nutzer", base_revision=0)
    put = proposals.put("testuser", bid, graph(3, "agent"), "")
    assert put["drawn"] is False and put["board"]["revision"] == 1
    # Die Fassung des Nutzers ist dieselbe: Er kann weiterzeichnen, während der Vorschlag offen liegt.
    assert _save(client, auth_headers, bid, 3, "nutzer", base_revision=1).status_code == 200


def test_uebernehmen_und_wiederherstellen_zaehlen_weiter(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    _save(client, auth_headers, bid, 2, "nutzer")
    proposals.put("testuser", bid, graph(3, "agent"), "")
    accepted = client.post(f"{BASE}/{bid}/proposal/accept", headers=auth_headers).json()
    assert accepted["revision"] == 2
    version_id = client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json()[0]["id"]
    restored = client.post(f"{BASE}/{bid}/versions/{version_id}/restore", headers=auth_headers).json()
    assert restored["revision"] == 3
    assert _save(client, auth_headers, bid, 1, "alt", base_revision=1).status_code == 409


def test_ohne_stand_speichert_ein_aelteres_fenster_wie_bisher(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    _save(client, auth_headers, bid, 2, "a")
    r = _save(client, auth_headers, bid, 1, "b")
    assert r.status_code == 200 and ids(r.json()["graph_json"]) == ["b0"]


def test_meine_fassung_behalten_sichert_die_andere(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    proposals.put("testuser", bid, graph(3, "agent"), "")
    kept = _save(client, auth_headers, bid, 1, "nutzer", keep_previous=True)
    assert kept.status_code == 200, kept.text
    assert ids(kept.json()["graph_json"]) == ["nutzer0"] and kept.json()["revision"] == 2
    listed = client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json()
    assert [(v["source"], v["node_count"]) for v in listed] == [("overwrite", 3)]
    restored = client.post(f"{BASE}/{bid}/versions/{listed[0]['id']}/restore", headers=auth_headers).json()
    assert ids(restored["graph_json"]) == ["agent0", "agent1", "agent2"]


def test_behalten_ohne_unterschied_legt_keine_fassung_ab(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    _save(client, auth_headers, bid, 2, "gleich")
    again = _save(client, auth_headers, bid, 2, "gleich", keep_previous=True)
    assert again.status_code == 200
    assert client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json() == []


def test_fremdes_board_bleibt_auch_mit_stand_unsichtbar(client, auth_headers):
    bid = _new(client, auth_headers)["id"]
    other = _h(client)
    for extra in ({"base_revision": 0}, {"base_revision": 7}, {"keep_previous": True}):
        r = _save(client, other, bid, 1, "fremd", **extra)
        assert r.status_code == 404 and _code(r) == "board_not_found", extra
    stored = client.get(f"{BASE}/{bid}", headers=auth_headers).json()
    assert stored["revision"] == 0 and ids(stored["graph_json"]) == []
    assert client.get(f"{BASE}/{bid}/versions", headers=auth_headers).json() == []


def test_bestehende_boards_bekommen_den_zaehler_null():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript((MIGRATIONS / "001_blueprint.sql").read_text(encoding="utf-8"))
        conn.execute('INSERT INTO module_blueprint_boards ("user", name) VALUES (?, ?)', ("testuser", "Vorher"))
        for name in ("002_project_proposal.sql", "003_versions.sql"):
            conn.executescript((MIGRATIONS / name).read_text(encoding="utf-8"))
        assert conn.execute("SELECT revision FROM module_blueprint_boards").fetchone()["revision"] == 0
    finally:
        conn.close()
