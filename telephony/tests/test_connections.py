"""Verbindung speichern, verbinden, trennen, löschen – über die API (PLAN-EINSTELLUNGEN Schritt 6)."""
from __future__ import annotations

import logging
import time

import pytest
from _fake_registrar import FakeRegistrar

pytestmark = pytest.mark.usefixtures("clean_rows")
BASE = "/api/modules/telephony/connection"


def _free_port() -> int:
    import socket

    for _ in range(50):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        if port >= 1024 and not 7078 <= port <= 7109:
            return port
    raise RuntimeError("kein freier Port")


_PORT = _free_port()


@pytest.fixture(autouse=True)
def _lan(monkeypatch):
    """fritz.box → 192.168.178.1 (Testnetz ohne DNS); alles andere echte Prüfung."""
    from backend import connections, netguard

    monkeypatch.setattr(connections, "_resolve_target",
                        lambda host: netguard.check(host, resolve=lambda h: ["192.168.178.1"] if h == "fritz.box"
                                                    else []))
    yield
    connections.MANAGER.stop_all()


@pytest.fixture
def reg(monkeypatch):
    """Echter Registrar auf 127.0.0.1; die Heimnetz-Prüfung wird für den Test auf 127.0.0.1 umgelenkt."""
    from backend import connections

    r = FakeRegistrar()
    monkeypatch.setattr(connections, "_resolve_target", lambda host: "127.0.0.1")
    monkeypatch.setattr(connections, "_bind_host", lambda: "127.0.0.1")
    yield r
    connections.MANAGER.stop_all()
    r.close()


def _body(reg: FakeRegistrar | None = None, **over) -> dict:
    d = {"pbx": "fritzbox", "registrar": "fritz.box", "registrar_port": reg.port if reg else 5060,
         "username": "hydra-telefon", "password": "Sehr-Geheim-42", "own_number": "030 1234567",
         "local_sip_port": _PORT, "rtp_port_min": 7078, "rtp_port_max": 7109, "register_interval": 300}
    d.update(over)
    return d


def _wait_status(client, headers, want: str, timeout: float = 5.0) -> dict:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        d = client.get(BASE, headers=headers).json()
        if d["status"] == want:
            return d
        time.sleep(0.05)
    return client.get(BASE, headers=headers).json()


def test_ohne_anmeldung_401(client) -> None:
    assert client.get(BASE).status_code == 401


def test_leer_wenn_nicht_eingerichtet(client, auth_headers) -> None:
    r = client.get(BASE, headers=auth_headers)
    assert r.status_code == 200 and r.json() == {"configured": False, "status": "not_configured"}


def test_speichern_ohne_kennwort_in_antwort(client, auth_headers) -> None:
    r = client.put(BASE, json=_body(local_sip_port=5070), headers=auth_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["configured"] and d["has_password"] and d["status"] == "disconnected"
    assert d["registrar"] == "fritz.box" and d["username"] == "hydra-telefon" and d["own_number"] == "030 1234567"
    assert "Sehr-Geheim-42" not in r.text and "secret" not in d and "password" not in d
    assert "Sehr-Geheim-42" not in client.get(BASE, headers=auth_headers).text


def test_kennwort_in_db_verschluesselt(client, auth_headers) -> None:
    from hydrahive.db.connection import db

    client.put(BASE, json=_body(), headers=auth_headers)
    with db() as c:
        row = c.execute("SELECT secret FROM module_telephony_connections").fetchone()
    assert row[0].startswith("tel:v1:") and "Sehr-Geheim-42" not in row[0]


def test_neu_anlegen_braucht_kennwort(client, auth_headers) -> None:
    r = client.put(BASE, json=_body(password=""), headers=auth_headers)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "password_required"


def test_aendern_ohne_kennwort_behaelt_altes(client, auth_headers, reg) -> None:
    client.put(BASE, json=_body(reg), headers=auth_headers)
    r = client.put(BASE, json=_body(reg, password="", own_number="030 999"), headers=auth_headers)
    assert r.status_code == 200 and r.json()["own_number"] == "030 999"
    assert client.post(f"{BASE}/connect", headers=auth_headers).json()["status"] == "registered"


def test_ungueltige_eingabe_422_ohne_kennwort_im_fehler(client, auth_headers) -> None:
    r = client.put(BASE, json=_body(registrar="http://x", password="Sehr-Geheim-42"), headers=auth_headers)
    assert r.status_code == 422 and "Sehr-Geheim-42" not in r.text


def test_validierungsfehler_enthaelt_keine_eingabewerte(client, auth_headers) -> None:
    r = client.put(BASE, json=_body(registrar="xx yy", password="Sehr-Geheim-42", display_name="Geheimer-Name"),
                   headers=auth_headers)
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["code"] == "invalid" and "registrar" in d["params"]["fields"]
    assert "input" not in r.text and "xx yy" not in r.text and "Geheimer-Name" not in r.text


def test_oeffentliche_adresse_wird_abgelehnt(client, auth_headers) -> None:
    r = client.put(BASE, json=_body(registrar="8.8.8.8"), headers=auth_headers)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "blocked"


def test_verbinden_und_trennen(client, auth_headers, reg) -> None:
    client.put(BASE, json=_body(reg), headers=auth_headers)
    r = client.post(f"{BASE}/connect", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "registered"
    assert client.get(BASE, headers=auth_headers).json()["enabled"] is True
    r = client.post(f"{BASE}/disconnect", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "disconnected" and r.json()["enabled"] is False
    assert reg.registers()[-1].header("expires") == "0"


def test_falsches_kennwort_wird_gemeldet(client, auth_headers, reg) -> None:
    client.put(BASE, json=_body(reg, password="Falsch-Falsch-1"), headers=auth_headers)
    assert client.post(f"{BASE}/connect", headers=auth_headers).json()["status"] == "auth_failed"


def test_aendern_waehrend_verbunden_verbindet_neu(client, auth_headers, reg) -> None:
    client.put(BASE, json=_body(reg), headers=auth_headers)
    client.post(f"{BASE}/connect", headers=auth_headers)
    n = len(reg.registers())
    client.put(BASE, json=_body(reg, password="", display_name="Büro"), headers=auth_headers)
    d = _wait_status(client, auth_headers, "registered")
    assert d["status"] == "registered" and len(reg.registers()) > n
    assert reg.registers()[-1].header("from").startswith('"Büro"')


def test_loeschen_meldet_ab(client, auth_headers, reg) -> None:
    client.put(BASE, json=_body(reg), headers=auth_headers)
    client.post(f"{BASE}/connect", headers=auth_headers)
    assert client.delete(BASE, headers=auth_headers).status_code == 204
    assert reg.registers()[-1].header("expires") == "0"
    assert client.get(BASE, headers=auth_headers).json()["configured"] is False


def test_jeder_sieht_nur_die_eigene(client, auth_headers, other_headers) -> None:
    client.put(BASE, json=_body(), headers=auth_headers)
    assert client.get(BASE, headers=other_headers).json()["configured"] is False
    assert client.post(f"{BASE}/connect", headers=other_headers).status_code == 404
    assert client.delete(BASE, headers=other_headers).status_code == 404
    assert client.get(BASE, headers=auth_headers).json()["configured"] is True


def test_verbinden_ohne_einrichtung_404(client, auth_headers) -> None:
    assert client.post(f"{BASE}/connect", headers=auth_headers).status_code == 404


def test_ratenbegrenzung_beim_verbinden(client, auth_headers, reg, monkeypatch) -> None:
    from hydrahive.api.middleware import inbound_ratelimit

    monkeypatch.setattr(inbound_ratelimit, "_hits", type(inbound_ratelimit._hits)(list))
    client.put(BASE, json=_body(reg), headers=auth_headers)
    codes = [client.post(f"{BASE}/connect", headers=auth_headers).status_code for _ in range(12)]
    assert 429 in codes and codes[0] == 200


def test_lokaler_port_doppelt_vergeben_409(client, auth_headers, other_headers) -> None:
    client.put(BASE, json=_body(local_sip_port=5090), headers=auth_headers)
    r = client.put(BASE, json=_body(local_sip_port=5090), headers=other_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "port_taken"


def test_kennwort_nie_im_log(client, auth_headers, reg, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    client.put(BASE, json=_body(reg), headers=auth_headers)
    client.post(f"{BASE}/connect", headers=auth_headers)
    client.put(BASE, json=_body(reg, password="Falsch-Falsch-1"), headers=auth_headers)
    client.post(f"{BASE}/connect", headers=auth_headers)
    assert "Sehr-Geheim-42" not in caplog.text and "Falsch-Falsch-1" not in caplog.text


def test_nach_neustart_wieder_verbinden(client, auth_headers, reg) -> None:
    """Modul-Job: Verbindungen mit „Verbinden“ (enabled) laufen nach einem Neustart von selbst wieder an."""
    from backend import connections

    client.put(BASE, json=_body(reg), headers=auth_headers)
    client.post(f"{BASE}/connect", headers=auth_headers)
    connections.MANAGER.stop_all()                       # „Neustart“: alle Threads weg
    assert connections.MANAGER.running() == []
    connections.reconcile()
    assert _wait_status(client, auth_headers, "registered")["status"] == "registered"


def test_job_startet_getrennte_nicht(client, auth_headers, reg) -> None:
    from backend import connections

    client.put(BASE, json=_body(reg), headers=auth_headers)
    connections.reconcile()
    time.sleep(0.3)
    assert connections.MANAGER.running() == [] and reg.registers() == []
