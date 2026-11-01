"""Schnittstellen: ansehen mit module.network, einrichten nur mit network.configure. Geheimnisse nie in Antworten."""
from __future__ import annotations

import pytest
from conftest import SECRET

P = "/api/modules/network"
FP = "ab" * 32


@pytest.fixture
def fake_cert(monkeypatch):
    from backend import pinned
    st = {"fp": FP, "fail": False, "hosts": []}

    async def fetch(host, port):
        st["hosts"].append((host, port))
        if st["fail"]:
            raise OSError("weg")
        return st["fp"]
    monkeypatch.setattr(pinned, "fetch_fingerprint", fetch)
    return st


def body(**kw):
    b = {"udm_url": "https://192.168.178.1", "udm_credential": "udm", "fritz_host": "192.168.3.1",
         "fritz_credential": "", "plan_down_mbit": 1000, "plan_up_mbit": 50, "plan_price_eur": 39.99}
    b.update(kw)
    return b


def test_nutzer_ohne_recht_darf_nicht_einrichten(client, user_headers, db_ready):
    assert client.get(f"{P}/settings", headers=user_headers).status_code == 403
    assert client.put(f"{P}/settings", json=body(), headers=user_headers).status_code == 403
    assert client.get(f"{P}/credentials", headers=user_headers).status_code == 403
    assert client.post(f"{P}/udm/fingerprint", json={}, headers=user_headers).status_code == 403
    assert client.post(f"{P}/sync", json={}, headers=user_headers).status_code == 403


def test_nutzer_mit_modul_darf_ansehen(client, user_headers, db_ready):
    r = client.get(f"{P}/overview", headers=user_headers)
    assert r.status_code == 200 and r.json()["configured"] is False
    assert client.get(f"{P}/outages?days=7", headers=user_headers).status_code == 200
    assert client.get(f"{P}/samples?hours=24", headers=user_headers).status_code == 200


def test_ohne_anmeldung(client, db_ready):
    assert client.get(f"{P}/overview").status_code == 401


def test_einrichten_speichern_ohne_geheimnis(client, admin_headers, safe, db_ready):
    r = client.put(f"{P}/settings", json=body(), headers=admin_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["udm_url"] == "https://192.168.178.1" and d["udm_credential"] == "udm" and d["udm_pin"] is None
    assert d["plan_up_mbit"] == 50 and d["fritz_credential"] is None
    assert SECRET not in r.text
    names = client.get(f"{P}/credentials", headers=admin_headers).json()["items"]
    assert {"udm", "fritz"} <= {n["name"] for n in names}
    assert SECRET not in client.get(f"{P}/credentials", headers=admin_headers).text


@pytest.mark.parametrize("patch,code", [({"udm_url": "https://8.8.8.8"}, "network_host_not_local"),
                                        ({"udm_url": "http://192.168.178.1"}, "network_url_invalid"),
                                        ({"udm_credential": "gibtsnicht"}, "network_credential_invalid"),
                                        ({"fritz_host": "1.2.3.4"}, "network_host_not_local"),
                                        ({"fritz_credential": "udm"}, "network_credential_invalid"),
                                        ({"plan_up_mbit": -1}, "network_value_invalid")])
def test_einrichten_falsch(client, admin_headers, safe, db_ready, patch, code):
    r = client.put(f"{P}/settings", json=body(**patch), headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == code


def test_fritz_zugang_basic_ok(client, admin_headers, safe, db_ready):
    r = client.put(f"{P}/settings", json=body(fritz_credential="fritz"), headers=admin_headers)
    assert r.status_code == 200 and r.json()["fritz_credential"] == "fritz"
    assert "fritz-Passwort-9" not in r.text


def test_zertifikat_abrufen_und_bestaetigen(client, admin_headers, safe, db_ready, fake_cert):
    client.put(f"{P}/settings", json=body(), headers=admin_headers)
    r = client.post(f"{P}/udm/fingerprint", json={}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["fingerprint"] == FP and fake_cert["hosts"] == [("192.168.178.1", 443)]
    assert r.json()["pretty"].startswith("AB:AB")
    bad = client.post(f"{P}/udm/confirm", json={"fingerprint": "cd" * 32}, headers=admin_headers)
    assert bad.status_code == 409 and bad.json()["detail"]["code"] == "network_fingerprint_mismatch"
    ok = client.post(f"{P}/udm/confirm", json={"fingerprint": FP}, headers=admin_headers)
    assert ok.status_code == 200 and ok.json()["udm_pin"] == FP
    # andere Adresse → Bestätigung weg
    r = client.put(f"{P}/settings", json=body(udm_url="https://192.168.178.2"), headers=admin_headers)
    assert r.json()["udm_pin"] is None
    # gleiche Adresse → bleibt
    client.post(f"{P}/udm/confirm", json={"fingerprint": FP}, headers=admin_headers)
    r = client.put(f"{P}/settings", json=body(udm_url="https://192.168.178.2", plan_up_mbit=40), headers=admin_headers)
    assert r.json()["udm_pin"] == FP


def test_zertifikat_ohne_einrichtung_oder_nicht_erreichbar(client, admin_headers, safe, db_ready, fake_cert):
    r = client.post(f"{P}/udm/fingerprint", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "network_not_configured"
    client.put(f"{P}/settings", json=body(), headers=admin_headers)
    fake_cert["fail"] = True
    r = client.post(f"{P}/udm/fingerprint", json={}, headers=admin_headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "network_unreachable"


class _Resp:
    def __init__(self, status, data):
        self.status_code, self._data = status, data

    def json(self):
        return self._data


def test_verbindung_testen(client, admin_headers, safe, db_ready, fake_cert, monkeypatch):
    from backend import unifi_client
    seen = []

    async def fake_send(method, url, *, headers, json, pin):
        seen.append({"key": headers.get("X-API-KEY"), "pin": pin, "url": url})
        return _Resp(200, {"applicationVersion": "10.6.109"})
    monkeypatch.setattr(unifi_client, "_send", fake_send)
    client.put(f"{P}/settings", json=body(), headers=admin_headers)
    r = client.post(f"{P}/udm/test", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "network_cert_unconfirmed" and seen == []
    client.post(f"{P}/udm/confirm", json={"fingerprint": FP}, headers=admin_headers)
    r = client.post(f"{P}/udm/test", json={}, headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"ok": True, "version": "10.6.109"}
    assert seen == [{"key": SECRET, "pin": FP, "url": "https://192.168.178.1/proxy/network/integration/v1/info"}]
    assert SECRET not in r.text


def test_verbindung_testen_abgelehnt(client, admin_headers, safe, db_ready, fake_cert, monkeypatch):
    from backend import unifi_client
    from backend.errors import NetError

    async def fake_get(self, path):
        raise NetError("network_auth_failed")
    monkeypatch.setattr(unifi_client.Udm, "get", fake_get)
    client.put(f"{P}/settings", json=body(), headers=admin_headers)
    client.post(f"{P}/udm/confirm", json={"fingerprint": FP}, headers=admin_headers)
    r = client.post(f"{P}/udm/test", json={}, headers=admin_headers)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "network_auth_failed"


def test_ueberblick_und_stoerungen(client, admin_headers, user_headers, safe, db_ready, udm_data):
    from backend import store, unifi_parse
    store.add_events(unifi_parse.events(udm_data["system_log"]))
    store.add_speedtests(unifi_parse.speedtests(udm_data["speedtests"]))
    store.add_sample({"ts": 1_793_560_000, "inet_loss": 0.0, "inet_rtt_avg": 20.0, "path": "cable"})
    client.put(f"{P}/settings", json=body(), headers=admin_headers)
    o = client.get(f"{P}/overview", headers=user_headers).json()
    assert o["configured"] is True and o["latest"]["path"] == "cable"
    assert o["plan"] == {"down": 1000, "up": 50}
    assert o["last_speedtest"]["up_mbit"] == 2.0
    assert "udm_credential" not in o and SECRET not in str(o)
    r = client.get(f"{P}/outages?days=90&now=1793570000", headers=user_headers).json()
    longest = max(r["items"], key=lambda x: x["end"] - x["start"])
    assert longest["end"] - longest["start"] == 8 * 3600 + 31 * 60 and longest["kind"] == "wan"
    assert r["per_day"]["2026-10-27"] >= 8 * 3600
    st = client.get(f"{P}/speedtests?days=90&now=1793570000", headers=user_headers).json()["items"]
    assert len(st) == 5


@pytest.mark.parametrize("q", ["days=0", "days=400", "hours=0", "hours=10000"])
def test_zeitraum_grenzen(client, user_headers, db_ready, q):
    path = "outages" if q.startswith("days") else "samples"
    assert client.get(f"{P}/{path}?{q}", headers=user_headers).status_code == 422


def test_import(client, admin_headers, user_headers, db_ready, udm_data):
    import json
    snap = {"system_log_90d": {"status": 200, "data": udm_data["system_log"]["data"]},
            "speedtest_90d": {"status": 200, "data": udm_data["speedtests"]}}
    files = {"file": ("udm.json", json.dumps(snap).encode(), "application/json")}
    assert client.post(f"{P}/import", files=files, headers=user_headers).status_code == 403
    r = client.post(f"{P}/import", files=files, headers=admin_headers)
    assert r.status_code == 200 and r.json()["speedtests"] == 5
    bad = client.post(f"{P}/import", files={"file": ("x.json", b"nein", "application/json")}, headers=admin_headers)
    assert bad.status_code == 400 and bad.json()["detail"]["code"] == "network_import_invalid"


def test_sofort_abrufen(client, admin_headers, safe, db_ready, monkeypatch):
    from backend import collect
    calls = []

    async def t_udm(now=None):
        calls.append("udm")

    async def t_h(now=None):
        calls.append("hourly")
        return {"events": 3, "speedtests": 1}
    monkeypatch.setattr(collect, "tick_udm", t_udm)
    monkeypatch.setattr(collect, "tick_hourly", t_h)
    r = client.post(f"{P}/sync", json={}, headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"events": 3, "speedtests": 1} and calls == ["udm", "hourly"]
