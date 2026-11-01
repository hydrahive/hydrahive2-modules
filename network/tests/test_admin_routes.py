"""Routen 0.2.0: Geräte, Clients, Netz, Verkehr. Ansehen mit module.network. Nie ein Geheimnis in einer Antwort."""
from __future__ import annotations

import pytest
from conftest_admin import ANSWERS

P = "/api/modules/network"
FP = "ab" * 32
LOCK = ("LOCKVOGEL", "x_passphrase", "x_authkey", "x_iapp_key")


@pytest.fixture
def udm(monkeypatch, client, admin_headers, safe, db_ready):
    from backend import admin_data, config_store, unifi_client
    admin_data.clear_cache()
    calls = []
    state = {"fail": None}

    async def fake_get(self, path):
        calls.append(path)
        if state["fail"]:
            from backend.errors import NetError
            raise NetError(state["fail"])
        return ANSWERS[path]
    monkeypatch.setattr(unifi_client.Udm, "get", fake_get)
    config_store.save(owner="boss", udm_url="https://192.168.178.1", udm_credential="udm", fritz_host=None,
                      fritz_credential=None, plan_down_mbit=None, plan_up_mbit=None, plan_price_eur=None)
    config_store.set_pin(FP)
    yield {"calls": calls, "state": state}
    admin_data.clear_cache()


@pytest.mark.parametrize("path", ["devices", "clients", "net", "traffic"])
def test_kein_geheimnis_in_der_antwort(client, user_headers, udm, path):
    r = client.get(f"{P}/{path}", headers=user_headers)
    assert r.status_code == 200, r.text
    for word in LOCK:
        assert word not in r.text, f"{word} in /{path}"


def test_geraete(client, user_headers, udm):
    d = client.get(f"{P}/devices", headers=user_headers).json()
    assert len(d["items"]) == 4 and d["items"][0]["name"] == "Dream Machine Pro"
    assert d["stale"] is False and d["fetched_at"] > 0


def test_clients_mit_filtern(client, user_headers, udm):
    d = client.get(f"{P}/clients", headers=user_headers).json()
    assert d["total"] == 71 and d["online"] == 42 and d["wireless"] == 20 and len(d["items"]) == 71
    on = client.get(f"{P}/clients?status=online", headers=user_headers).json()["items"]
    assert len(on) == 42 and all(c["online"] for c in on)
    wl = client.get(f"{P}/clients?status=online&link=wireless", headers=user_headers).json()["items"]
    assert len(wl) == 20 and not any(c["wired"] for c in wl)
    off = client.get(f"{P}/clients?status=offline", headers=user_headers).json()["items"]
    assert len(off) == 29
    q = client.get(f"{P}/clients?q=tuya", headers=user_headers).json()["items"]
    assert q and all("tuya" in (c["vendor"] or "").lower() or "tuya" in c["name"].lower() for c in q)
    q = client.get(f"{P}/clients?q=10.0.0.214", headers=user_headers).json()["items"]
    assert len(q) == 1 and q[0]["wired"]


@pytest.mark.parametrize("q", ["status=weg", "link=funk", f"q={'x' * 101}"])
def test_clients_falsche_filter(client, user_headers, udm, q):
    assert client.get(f"{P}/clients?{q}", headers=user_headers).status_code == 422


def test_netz(client, user_headers, udm):
    d = client.get(f"{P}/net", headers=user_headers).json()
    assert d["tree"][0]["name"] == "Dream Machine Pro"
    assert d["wlans"][0]["name"] == "Heimnetz" and d["forwards"][0]["name"] == "plex"


def test_verkehr(client, user_headers, udm):
    d = client.get(f"{P}/traffic", headers=user_headers).json()
    top = d["clients"]
    assert len(top) == 20
    totals = [c["down_bytes"] + c["up_bytes"] for c in top]
    assert totals == sorted(totals, reverse=True)
    assert d["devices"][0]["name"] == "Dream Machine Pro"
    assert len(d["devices"]) == 3  # nicht übernommener Switch fehlt
    assert any(p["tx_bytes"] for dev in d["devices"] for p in dev["ports"])


def test_zwischenspeicher_30s(client, user_headers, udm, monkeypatch):
    from backend import admin_data
    t = {"now": 1000.0}
    monkeypatch.setattr(admin_data, "_clock", lambda: t["now"])
    admin_data.clear_cache()
    client.get(f"{P}/devices", headers=user_headers)
    n = len(udm["calls"])
    client.get(f"{P}/clients", headers=user_headers)
    client.get(f"{P}/devices", headers=user_headers)
    assert len(udm["calls"]) == n + 2  # clients holt nur sta + user nach, devices aus dem Speicher
    t["now"] += 31
    client.get(f"{P}/devices", headers=user_headers)
    assert len(udm["calls"]) == n + 3


def test_nicht_erreichbar_zeigt_letzten_stand(client, user_headers, udm, monkeypatch):
    from backend import admin_data
    t = {"now": 1000.0}
    monkeypatch.setattr(admin_data, "_clock", lambda: t["now"])
    admin_data.clear_cache()
    assert client.get(f"{P}/devices", headers=user_headers).json()["stale"] is False
    t["now"] += 60
    udm["state"]["fail"] = "network_unreachable"
    d = client.get(f"{P}/devices", headers=user_headers).json()
    assert d["stale"] is True and d["error"] == "network_unreachable" and len(d["items"]) == 4


def test_nicht_erreichbar_ohne_stand(client, user_headers, udm):
    udm["state"]["fail"] = "network_unreachable"
    r = client.get(f"{P}/devices", headers=user_headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "network_unreachable"


def test_nicht_eingerichtet(client, user_headers, db_ready):
    from backend import admin_data
    admin_data.clear_cache()
    r = client.get(f"{P}/devices", headers=user_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "network_not_configured"


def test_ohne_anmeldung(client, db_ready):
    assert client.get(f"{P}/devices").status_code == 401


def test_ueberblick_mit_zahlen(client, user_headers, udm):
    client.get(f"{P}/devices", headers=user_headers)
    client.get(f"{P}/clients", headers=user_headers)
    o = client.get(f"{P}/overview", headers=user_headers).json()
    assert o["counts"] == {"devices": 4, "devices_online": 3, "clients": 42, "wireless": 20, "wired": 22}
