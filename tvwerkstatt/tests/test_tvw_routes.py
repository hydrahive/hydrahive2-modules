"""Baustein 1: Schnittstelle /api/modules/tvwerkstatt – nur Admins, ohne incus klare Meldung (PLAN-E1.md)."""
from __future__ import annotations

import pytest
from backend import incus

B = "/api/modules/tvwerkstatt"


def test_state_nur_admins(client, user_headers):
    assert client.get(B + "/state", headers=user_headers).status_code == 403


def test_state_ohne_anmeldung(client):
    assert client.get(B + "/state").status_code in (401, 403)


@pytest.fixture
def user_with_module_grant(db_ready):
    """Ein Admin gibt das Modul versehentlich einem normalen Nutzer frei – die Schnittstelle muss trotzdem sperren."""
    from hydrahive.access import grants
    from hydrahive.api.middleware.users import get_by_username
    uid = get_by_username("testuser")["user_id"]
    grants.grant("module.tvwerkstatt", "user", uid, "use", actor_id="test")
    yield
    grants.revoke("module.tvwerkstatt", "user", uid, actor_id="test")


def test_state_auch_mit_freigabe_nur_admin(client, user_headers, user_with_module_grant):
    assert client.get(B + "/state", headers=user_headers).status_code == 403


def test_state_mit_incus(client, admin_headers, monkeypatch):
    monkeypatch.setattr(incus, "available", lambda: True)
    r = client.get(B + "/state", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["incus"] is True and d["error_code"] == ""
    assert d["devices"] == [] and d["builds"] == []


def test_state_ohne_incus_klare_meldung(client, admin_headers, monkeypatch):
    """Ohne incus kein Fehler 500, sondern ein Zustand, den die Seite erklären kann."""
    monkeypatch.setattr(incus, "available", lambda: False)
    r = client.get(B + "/state", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["incus"] is False and d["error_code"] == "tvw_no_incus"


def test_state_zeigt_geraete_ohne_interna(client, admin_headers, monkeypatch, db_ready):
    monkeypatch.setattr(incus, "available", lambda: True)
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, kind, android, created_by) "
                     "VALUES ('d1', 'Wohnzimmer', '192.0.2.10', 'android_tv', '9', 'boss')")
        conn.commit()
    d = client.get(B + "/state", headers=admin_headers).json()
    assert [x["device_id"] for x in d["devices"]] == ["d1"]
    dev = d["devices"][0]
    assert dev["name"] == "Wohnzimmer" and dev["address"] == "192.0.2.10" and dev["android"] == "9"
    assert "created_by" not in dev
