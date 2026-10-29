"""Routen /api/modules/fernseher/* (SPEC.md „Seite“, „Freigaben“)."""
from __future__ import annotations

import pytest
from conftest import PSK, login

P = "/api/modules/fernseher"


def test_einstellungen_lesen_ohne_schluessel(client, configured):
    r = client.get(f"{P}/settings", headers=login(client, "testuser"))
    assert r.status_code == 200
    assert r.json() == {"configured": True, "name": "TV Wohnzimmer", "address": "192.168.178.186",
                        "psk_set": True, "volume_limit": 60}
    assert PSK not in r.text


def test_einstellungen_speichern_nur_admin(client, fake_tv):
    body = {"name": "TV", "address": "192.168.178.186", "psk": "neu-1", "volume_limit": 50}
    assert client.put(f"{P}/settings", json=body, headers=login(client, "testuser")).status_code == 403
    r = client.put(f"{P}/settings", json=body, headers=login(client, "admin"))
    assert r.status_code == 200 and r.json()["psk_set"] is True and "neu-1" not in r.text


def test_einstellungen_oeffentliche_adresse_abgelehnt(client, fake_tv):
    body = {"name": "TV", "address": "8.8.8.8", "psk": "x", "volume_limit": 50}
    r = client.put(f"{P}/settings", json=body, headers=login(client, "admin"))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tv_address_not_local"


def test_erstes_speichern_braucht_schluessel(client, fake_tv):
    body = {"name": "TV", "address": "192.168.178.186", "volume_limit": 50}
    r = client.put(f"{P}/settings", json=body, headers=login(client, "admin"))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tv_psk_missing"


def test_verbindung_testen(client, configured):
    assert client.post(f"{P}/test", headers=login(client, "testuser")).status_code == 403
    r = client.post(f"{P}/test", headers=login(client, "admin"))
    assert r.status_code == 200 and r.json() == {"ok": True, "model": "KD-60XF8305", "power": "on"}


def test_status_und_listen_fuer_alle(client, configured):
    h = login(client, "testuser")
    assert client.get(f"{P}/status", headers=h).json()["channel"]["name"] == "SAT.1"
    chs = client.get(f"{P}/channels", headers=h).json()
    assert len(chs) == 6 and chs[1] == {"number": 2, "name": "ZDF HD"}      # ohne interne Sony-Adresse (uri)
    assert client.get(f"{P}/apps", headers=h).json()[0] == {"name": "Netflix"}


@pytest.mark.parametrize(("code", "status"), [("needs_restart", 409), ("unreachable", 504)])
def test_fehler_als_klare_codes(client, configured, code, status):
    configured.mode = code
    r = client.get(f"{P}/status", headers=login(client, "testuser"))
    assert r.status_code == status and r.json()["detail"]["code"] == f"tv_{code}"


def test_falscher_schluessel(client, configured):
    configured.psk = "anders"
    r = client.get(f"{P}/status", headers=login(client, "testuser"))
    assert r.status_code == 502 and r.json()["detail"]["code"] == "tv_auth_failed" and PSK not in r.text


def test_nicht_eingerichtet(client, fake_tv):
    r = client.get(f"{P}/status", headers=login(client, "testuser"))
    assert r.status_code == 503 and r.json()["detail"]["code"] == "tv_not_configured"


def test_ohne_login(client, configured):
    assert client.get(f"{P}/status").status_code == 401


def test_admin_schaltet(client, configured):
    h = login(client, "admin")
    assert client.post(f"{P}/channel", json={"sender": "ZDF"}, headers=h).json()["channel"]["number"] == 2
    assert client.post(f"{P}/volume", json={"wert": "+2"}, headers=h).json()["volume"] == 16
    assert client.post(f"{P}/mute", json={"stumm": True}, headers=h).json()["muted"] is True
    assert client.post(f"{P}/power", json={"an": False}, headers=h).json()["power"] == "standby"
    assert client.post(f"{P}/app", json={"name": "Plex"}, headers=h).json() == {"started": "Plex"}


def test_lautstaerke_grenze_400(client, configured):
    r = client.post(f"{P}/volume", json={"wert": "99"}, headers=login(client, "admin"))
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tv_volume_limit"


def test_umschalten_nicht_gelungen_409(client, configured):
    configured.ignore_switch = True
    r = client.post(f"{P}/channel", json={"sender": "ZDF"}, headers=login(client, "admin"))
    assert r.status_code == 409 and r.json()["detail"]["code"] == "tv_switch_failed"
