"""Kopplung per QR: Einmal-Code → eigener API-Key der Brille."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from conftest import DEV_PREFIX, MOD_PREFIX


def _pair(client, headers, name="Quest 3"):
    r = client.post(f"{MOD_PREFIX}/pairing", json={"name": name}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def _redeem(client, code):
    return client.post(f"{DEV_PREFIX}/redeem", headers={"X-VR-Pair": code})


def test_pairing_requires_login(client):
    assert client.post(f"{MOD_PREFIX}/pairing", json={}).status_code == 401
    assert client.get(f"{MOD_PREFIX}/headsets").status_code == 401


def test_qr_contains_code_but_no_key(client, login):
    p = _pair(client, login("alice"))
    assert len(p["code"]) == 14 and p["code"].count("-") == 2
    assert isinstance(p["qr"], list) and len(p["qr"]) >= 21
    assert "api_key" not in p and "hhk_" not in str(p)


def test_redeem_gives_working_key_for_creator(client, login):
    p = _pair(client, login("alice"))
    r = _redeem(client, p["code"])
    assert r.status_code == 200
    key = r.json()["api_key"]
    assert key.startswith("hhk_") and r.json()["username"] == "alice"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {key}"})
    assert me.status_code == 200 and me.json()["username"] == "alice"


def test_code_is_single_use(client, login):
    p = _pair(client, login("alice"))
    assert _redeem(client, p["code"]).status_code == 200
    assert _redeem(client, p["code"]).status_code == 401


def test_expired_code_is_rejected(client, login):
    p = _pair(client, login("alice"))
    from hydrahive.db.connection import db
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with db() as c:
        c.execute("UPDATE module_vr_pairing SET expires_at = ?", (past,))
    assert _redeem(client, p["code"]).status_code == 401


@pytest.mark.parametrize("code", [None, "", "abc", "ZZZZ-ZZZZ-ZZZZ"])
def test_wrong_or_missing_code(client, code):
    headers = {} if code is None else {"X-VR-Pair": code}
    assert client.post(f"{DEV_PREFIX}/redeem", headers=headers).status_code == 401


def test_headsets_are_per_user_and_removal_revokes_key(client, login):
    a, b = login("alice"), login("bob")
    key = _redeem(client, _pair(client, a, "Alice-Quest")["code"]).json()["api_key"]
    hs = client.get(f"{MOD_PREFIX}/headsets", headers=a).json()
    assert [h["name"] for h in hs] == ["Alice-Quest"]
    assert client.get(f"{MOD_PREFIX}/headsets", headers=b).json() == []        # bob sieht nichts
    assert client.delete(f"{MOD_PREFIX}/headsets/{hs[0]['id']}", headers=b).status_code == 404  # bob darf nicht
    assert client.delete(f"{MOD_PREFIX}/headsets/{hs[0]['id']}", headers=a).status_code == 200
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {key}"}).status_code == 401  # Key tot


def test_open_code_limit(client, login):
    a = login("alice")
    for _ in range(5):
        _pair(client, a)
    assert client.post(f"{MOD_PREFIX}/pairing", json={"name": "x"}, headers=a).status_code == 400


def test_invalid_name(client, login):
    r = client.post(f"{MOD_PREFIX}/pairing", json={"name": "<script>"}, headers=login("alice"))
    assert r.status_code == 400
