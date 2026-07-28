"""Voice-Modul E1 — Status-Endpoint + Auth-Guard."""
from __future__ import annotations

PREFIX = "/api/modules/voice"


def test_status_braucht_auth(client):
    assert client.get(f"{PREFIX}/status").status_code == 401


def test_status_ok_fuer_user(client, user_headers):
    r = client.get(f"{PREFIX}/status", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["module"] == "voice"
    assert body["stage"] == "e2"


def test_status_ok_fuer_admin(client, admin_headers):
    r = client.get(f"{PREFIX}/status", headers=admin_headers)
    assert r.status_code == 200
