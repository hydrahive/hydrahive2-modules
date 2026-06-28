"""Routen-Tests — Auth, Board-CRUD, graph_json-Validierung, Ownership."""
from __future__ import annotations

import json

BASE = "/api/modules/blueprint/boards"
_GRAPH = json.dumps({"nodes": [{"id": "a", "type": "layoutNode"}], "edges": []})


def _h(client, user="testuser"):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- Auth ----
def test_list_requires_auth(client):
    assert client.get(BASE).status_code in (401, 403)


# ---- CRUD ----
def test_create_and_get(client, auth_headers):
    r = client.post(BASE, json={"name": "Mein Board"}, headers=auth_headers)
    assert r.status_code == 201
    bid = r.json()["id"]
    assert r.json()["name"] == "Mein Board"

    g = client.get(f"{BASE}/{bid}", headers=auth_headers)
    assert g.status_code == 200
    assert g.json()["graph_json"] == '{"nodes":[],"edges":[]}'


def test_list_returns_metadata_only(client, auth_headers):
    client.post(BASE, json={"name": "B1"}, headers=auth_headers)
    rows = client.get(BASE, headers=auth_headers).json()
    assert len(rows) == 1
    assert "graph_json" not in rows[0]  # Liste ohne schweren Graphen


def test_update_graph(client, auth_headers):
    bid = client.post(BASE, json={"name": "B"}, headers=auth_headers).json()["id"]
    r = client.put(f"{BASE}/{bid}", json={"graph_json": _GRAPH}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["graph_json"] == _GRAPH


def test_update_name(client, auth_headers):
    bid = client.post(BASE, json={"name": "Alt"}, headers=auth_headers).json()["id"]
    r = client.put(f"{BASE}/{bid}", json={"name": "Neu"}, headers=auth_headers)
    assert r.json()["name"] == "Neu"


def test_delete(client, auth_headers):
    bid = client.post(BASE, json={"name": "B"}, headers=auth_headers).json()["id"]
    assert client.delete(f"{BASE}/{bid}", headers=auth_headers).json()["removed"] is True
    assert client.get(f"{BASE}/{bid}", headers=auth_headers).status_code == 404


# ---- Validierung ----
def test_invalid_json_rejected(client, auth_headers):
    bid = client.post(BASE, json={"name": "B"}, headers=auth_headers).json()["id"]
    r = client.put(f"{BASE}/{bid}", json={"graph_json": "{kaputt"}, headers=auth_headers)
    assert r.status_code == 400


def test_invalid_shape_rejected(client, auth_headers):
    bid = client.post(BASE, json={"name": "B"}, headers=auth_headers).json()["id"]
    # gültiges JSON, aber ohne nodes/edges
    r = client.put(f"{BASE}/{bid}", json={"graph_json": '{"foo":1}'}, headers=auth_headers)
    assert r.status_code == 400


def test_get_unknown_404(client, auth_headers):
    assert client.get(f"{BASE}/9999", headers=auth_headers).status_code == 404


# ---- Ownership ----
def test_boards_isolated_per_user(client):
    h1, h2 = _h(client, "testuser"), _h(client, "other")
    bid = client.post(BASE, json={"name": "Privat"}, headers=h1).json()["id"]

    # other sieht es nicht in der Liste
    assert client.get(BASE, headers=h2).json() == []
    # und kann es nicht lesen/ändern/löschen
    assert client.get(f"{BASE}/{bid}", headers=h2).status_code == 404
    assert client.put(f"{BASE}/{bid}", json={"name": "Hack"}, headers=h2).status_code == 404
    assert client.delete(f"{BASE}/{bid}", headers=h2).status_code == 404
