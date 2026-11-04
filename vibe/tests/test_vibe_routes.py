"""Baustein 1: Schnittstelle /api/modules/vibe – nur Admins, ohne incus klare Meldung (PLAN-V1.md)."""
from __future__ import annotations

import pytest
from backend import incus

B = "/api/modules/vibe"


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
    grants.grant("module.vibe", "user", uid, "use", actor_id="test")
    yield
    grants.revoke("module.vibe", "user", uid, actor_id="test")


def test_state_auch_mit_freigabe_nur_admin(client, user_headers, user_with_module_grant):
    assert client.get(B + "/state", headers=user_headers).status_code == 403


def test_state_mit_incus(client, admin_headers, fake_incus):
    r = client.get(B + "/state", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["incus"] is True and d["projects"] == []


def test_state_ohne_incus_klare_meldung(client, admin_headers, monkeypatch):
    """Mac ohne Colima u. a.: kein Fehler 500, sondern ein Zustand, den die Seite erklären kann."""
    monkeypatch.setattr(incus, "available", lambda: False)
    r = client.get(B + "/state", headers=admin_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["incus"] is False and d["error_code"] == "vibe_no_incus" and d["projects"] == []


def test_state_listet_nur_eigene_projekte_ohne_interna(client, admin_headers, fake_incus, db_ready):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_vibe_projects (project_id, agent_id, container, name, owner) "
                     "VALUES ('p1','a1','hh-vibe-p1','Meine App','boss')")
        conn.execute("INSERT INTO module_vibe_projects (project_id, agent_id, container, name, owner) "
                     "VALUES ('p2','a2','hh-vibe-p2','Fremd','jemand')")
        conn.commit()
    d = client.get(B + "/state", headers=admin_headers).json()
    assert [p["project_id"] for p in d["projects"]] == ["p1"]
    p = d["projects"][0]
    assert p["name"] == "Meine App"
    assert "container" not in p and "agent_id" not in p        # keine Interna nach außen
    assert "owner" not in p


def test_anlegen_ist_in_baustein_1_noch_nicht_da(client, admin_headers, fake_incus):
    """Projekte entstehen erst mit Baustein 4; bis dahin darf nichts angelegt werden."""
    r = client.post(B + "/projects", headers=admin_headers, json={"name": "x"})
    assert r.status_code in (404, 405)
    assert fake_incus.calls == []
