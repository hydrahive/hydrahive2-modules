"""Anrufe annehmen – Einstellungen, Testfenster, Anrufliste, Bestätigung (PLAN-ANRUFE-2A Schritt 7)."""
from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.usefixtures("clean_rows")
BASE = "/api/modules/telephony/connection"


@pytest.fixture(autouse=True)
def _lan(monkeypatch):
    from backend import connections, netguard

    monkeypatch.setattr(connections, "_resolve_target",
                        lambda host: netguard.check(host, resolve=lambda h: ["192.168.178.1"]))
    yield
    connections.MANAGER.stop_all()


def _setup(client, headers, **calls) -> None:
    r = client.put(BASE, json={"registrar": "fritz.box", "username": "hydra-telefon", "password": "Sehr-Geheim-42"},
                   headers=headers)
    assert r.status_code == 200, r.text
    if calls:
        r = client.put(f"{BASE}/calls", json=calls, headers=headers)
        assert r.status_code == 200, r.text


def test_standard_anrufe_aus_mit_vorgabe_ansage(client, auth_headers) -> None:
    _setup(client, auth_headers)
    d = client.get(BASE, headers=auth_headers).json()
    assert d["answer_calls"] is False and d["test_until"] is None
    assert d["greeting"] == "" and "HydraHive" in d["greeting_default"]


def test_schalter_und_ansage_speichern(client, auth_headers) -> None:
    _setup(client, auth_headers, answer_calls=True, greeting="Guten Tag, hier ist HydraHive.")
    d = client.get(BASE, headers=auth_headers).json()
    assert d["answer_calls"] is True and d["greeting"] == "Guten Tag, hier ist HydraHive."


@pytest.mark.parametrize("greeting", ["x" * 501, "a\x00b"])
def test_ansage_begrenzt(client, auth_headers, greeting: str) -> None:
    _setup(client, auth_headers)
    r = client.put(f"{BASE}/calls", json={"answer_calls": True, "greeting": greeting}, headers=auth_headers)
    assert r.status_code == 422


def test_ohne_verbindung_404(client, auth_headers) -> None:
    assert client.put(f"{BASE}/calls", json={"answer_calls": True}, headers=auth_headers).status_code == 404
    assert client.post(f"{BASE}/test-call", headers=auth_headers).status_code == 404


def test_policy_liefert_ansage_nur_wenn_an_oder_testfenster(client, auth_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    assert calls.policy(cid) is None
    client.put(f"{BASE}/calls", json={"answer_calls": True, "greeting": ""}, headers=auth_headers)
    assert "HydraHive" in calls.policy(cid), "leer = Vorgabe-Ansage"
    client.put(f"{BASE}/calls", json={"answer_calls": False, "greeting": "Eigene Ansage"}, headers=auth_headers)
    assert calls.policy(cid) is None
    r = client.post(f"{BASE}/test-call", headers=auth_headers)
    assert r.status_code == 200 and r.json()["test_until"]
    assert calls.policy(cid) == "Eigene Ansage", "Testfenster nimmt an, auch wenn der Schalter aus ist"


def test_testfenster_laeuft_ab_und_gilt_nur_fuer_einen_anruf(client, auth_headers, monkeypatch) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    client.post(f"{BASE}/test-call", headers=auth_headers)
    calls.record(cid, {"number": "•••567", "result": "answered", "codec": "PCMA", "rtp_out": 50, "rtp_in": 40})
    assert calls.policy(cid) is None, "nach dem Testanruf ist das Fenster zu"
    client.post(f"{BASE}/test-call", headers=auth_headers)
    monkeypatch.setattr(calls, "_now", lambda: time.time() + 120)
    assert calls.policy(cid) is None, "nach 60 s abgelaufen"


def test_anrufliste_maskiert_und_test_bestaetigen(client, auth_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    client.post(f"{BASE}/test-call", headers=auth_headers)
    calls.record(cid, {"number": "•••567", "result": "answered", "codec": "PCMA", "rtp_out": 50, "rtp_in": 40})
    calls.record(cid, {"number": "unbekannt", "result": "rejected"})
    items = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"]
    assert [c["result"] for c in items] == ["rejected", "answered"]
    test = items[1]
    assert test["is_test"] is True and test["heard"] is None and test["number"] == "•••567"
    r = client.post(f"{BASE}/calls/{test['id']}/heard", json={"heard": True}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["heard"] is True
    assert client.post(f"{BASE}/calls/{items[0]['id']}/heard", json={"heard": True},
                       headers=auth_headers).status_code == 409, "nur Testanrufe bestätigen"


def test_anrufliste_nur_eigene(client, auth_headers, other_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    calls.record(cid, {"number": "•••567", "result": "rejected"})
    cid2 = None
    r = client.put(BASE, json={"registrar": "fritz.box", "username": "hydra-telefon2", "password": "Sehr-Geheim-42",
                               "local_sip_port": 5071}, headers=other_headers)
    assert r.status_code == 200
    cid2 = connections._row("user:user-other")["id"]
    assert client.get(f"{BASE}/calls", headers=other_headers).json()["calls"] == []
    own_id = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"][0]["id"]
    assert client.post(f"{BASE}/calls/{own_id}/heard", json={"heard": True}, headers=other_headers).status_code == 404
    assert cid2 != cid


def test_hoechstens_50_eintraege(client, auth_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    for i in range(60):
        calls.record(cid, {"number": f"•••{i:03d}", "result": "rejected"})
    items = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"]
    assert len(items) == 50 and items[0]["number"] == "•••059"
    from hydrahive.db.connection import db
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_telephony_calls WHERE connection_id=?", (cid,)).fetchone()[0] == 50


def test_record_unbekannte_verbindung_still(client, auth_headers) -> None:
    from backend import calls

    calls.record("gibt-es-nicht", {"number": "x", "result": "rejected"})   # kein Fehler, kein Eintrag


def test_loeschen_nimmt_anrufliste_mit(client, auth_headers) -> None:
    from hydrahive.db.connection import db

    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    calls.record(cid, {"number": "•••567", "result": "rejected"})
    client.delete(BASE, headers=auth_headers)
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_telephony_calls WHERE connection_id=?", (cid,)).fetchone()[0] == 0


def test_agent_bekommt_policy_und_rtp_bereich(client, auth_headers) -> None:
    from backend import connections

    _setup(client, auth_headers)
    cfg = connections._config(connections._row("user:user-owner"))
    assert cfg["rtp_ports"] == (7078, 7109)
    assert callable(cfg["call_policy"]) and callable(cfg["call_record"])
    from backend.conn_manager import fingerprint
    a = fingerprint(cfg)
    client.put(f"{BASE}/calls", json={"answer_calls": True, "greeting": "Neu"}, headers=auth_headers)
    assert fingerprint(connections._config(connections._row("user:user-owner"))) == a, \
        "Schalter/Ansage ändern meldet nicht neu an"
