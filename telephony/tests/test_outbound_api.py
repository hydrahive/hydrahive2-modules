"""Anrufen per Knopf – API, Grenzen, Freigaben, Anrufliste (PLAN-ANRUFEN-3 Schritt 4). Nur Platzhalter-Nummern."""
from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.usefixtures("clean_rows")
BASE = "/api/modules/telephony/connection"


class FakeCall:
    def __init__(self, number: str, on_end) -> None:
        self.number, self.state, self.result, self.alive = number, "ringing", "", True
        self._on_end, self.hung = on_end, False

    def hangup(self) -> None:
        self.hung = True

    def finish(self, result: str) -> None:
        self.state, self.result, self.alive = "ended", result, False
        if self._on_end:
            self._on_end(self)


class FakeAgent:
    status = "registered"

    def __init__(self) -> None:
        self.dialed: list[tuple[str, str]] = []
        self.calls: list[FakeCall] = []
        self.busy = False

    def dial(self, number: str, audio, *, on_end=None, **options):
        from backend.sip.agent import LineBusy

        if self.busy:
            raise LineBusy()
        self.dialed.append((number, audio("PCMA")))
        c = FakeCall(number, on_end)
        self.calls.append(c)
        return c


@pytest.fixture(autouse=True)
def _lan(monkeypatch):
    from backend import connections, netguard, outbound

    monkeypatch.setattr(connections, "_resolve_target",
                        lambda host: netguard.check(host, resolve=lambda h: ["192.168.178.1"]))
    monkeypatch.setattr(outbound, "_render", lambda text, codec: text.encode())
    outbound._ACTIVE.clear()
    outbound._LAST_DIAL.clear()
    yield
    connections.MANAGER.stop_all()


@pytest.fixture
def agent(monkeypatch):
    from backend import outbound

    a = FakeAgent()
    monkeypatch.setattr(outbound, "_agent", lambda cid: a)
    return a


def _setup(client, headers) -> None:
    r = client.put(BASE, json={"registrar": "fritz.box", "username": "hydra-telefon", "password": "Sehr-Geheim-42"},
                   headers=headers)
    assert r.status_code == 200, r.text


def _dial(client, headers, number="030 1234567", text=""):
    return client.post(f"{BASE}/dial", json={"number": number, "text": text}, headers=headers)


def test_waehlt_normalisiert_und_meldet_status(client, auth_headers, agent) -> None:
    _setup(client, auth_headers)
    r = _dial(client, auth_headers, "+49 30 1234567", "Erinnerung: Termin morgen.")
    assert r.status_code == 200, r.text
    assert agent.dialed[0][0] == "0301234567"
    assert r.json()["number"] == "•••567" and r.json()["state"] == "ringing"
    s = client.get(f"{BASE}/dial", headers=auth_headers).json()
    assert s == {"active": True, "state": "ringing", "number": "•••567", "result": ""}
    agent.calls[0].finish("answered")
    s = client.get(f"{BASE}/dial", headers=auth_headers).json()
    assert s["active"] is False and s["result"] == "answered"


def test_volle_nummer_nirgends_gespeichert_oder_ausgegeben(client, auth_headers, agent) -> None:
    from hydrahive.db.connection import db

    _setup(client, auth_headers)
    r = _dial(client, auth_headers)
    assert "1234567" not in r.text
    with db() as c:
        dump = repr([tuple(x) for x in c.execute("SELECT * FROM module_telephony_connections").fetchall()])
    assert "1234567" not in dump


def test_ansage_text_geht_an_die_sprachausgabe_leer_gibt_vorgabe(client, auth_headers, agent, monkeypatch) -> None:
    from backend import outbound

    _setup(client, auth_headers)
    _dial(client, auth_headers, text="Hallo Welt")
    assert agent.dialed[0][1] == b"Hallo Welt"
    agent.calls[0].finish("answered")
    monkeypatch.setattr(outbound, "_now", lambda: time.time() + outbound.MIN_GAP_SECONDS + 1)
    _dial(client, auth_headers, text="")
    assert b"Assistent" in agent.dialed[1][1] and b"KI" in agent.dialed[1][1]


@pytest.mark.parametrize("number, code", [("112", "emergency"), ("**610", "invalid"), ("0900 1234567", "premium"),
                                          ("+43 1 2345678", "foreign"), ("1234567", "no_area_code"), ("abc", "invalid")])
def test_gesperrte_nummern(client, auth_headers, agent, number: str, code: str) -> None:
    _setup(client, auth_headers)
    r = _dial(client, auth_headers, number)
    assert r.status_code == 400 and r.json()["detail"]["code"] == f"number_{code}", r.text
    assert agent.dialed == []


def test_freigaben_premium_und_ausland(client, auth_headers, agent) -> None:
    from backend import outbound

    _setup(client, auth_headers)
    r = client.put(f"{BASE}/dial-rules", json={"allow_premium": True, "allow_foreign": True}, headers=auth_headers)
    assert r.status_code == 200
    assert client.get(BASE, headers=auth_headers).json()["allow_premium"] is True
    assert _dial(client, auth_headers, "+43 1 2345678").status_code == 200
    agent.calls[0].finish("answered")
    outbound._LAST_DIAL.clear()
    assert _dial(client, auth_headers, "112").status_code == 400, "Notruf auch mit Freigabe nie"


def test_standard_ohne_freigaben(client, auth_headers) -> None:
    _setup(client, auth_headers)
    d = client.get(BASE, headers=auth_headers).json()
    assert d["allow_premium"] is False and d["allow_foreign"] is False


def test_nicht_angemeldet(client, auth_headers, monkeypatch) -> None:
    from backend import outbound

    _setup(client, auth_headers)
    monkeypatch.setattr(outbound, "_agent", lambda cid: None)
    r = _dial(client, auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_registered"


def test_verbindung_da_aber_nicht_angemeldet(client, auth_headers, agent) -> None:
    _setup(client, auth_headers)
    agent.status = "auth_failed"
    r = _dial(client, auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_registered"
    assert agent.dialed == []


def test_leitung_belegt(client, auth_headers, agent) -> None:
    _setup(client, auth_headers)
    agent.busy = True
    r = _dial(client, auth_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "line_busy"


def test_abstand_zwischen_waehlversuchen(client, auth_headers, agent, monkeypatch) -> None:
    from backend import outbound

    _setup(client, auth_headers)
    assert _dial(client, auth_headers).status_code == 200
    agent.calls[0].finish("busy")
    r = _dial(client, auth_headers)
    assert r.status_code == 429 and r.json()["detail"]["code"] == "too_fast"
    monkeypatch.setattr(outbound, "_now", lambda: time.time() + outbound.MIN_GAP_SECONDS + 1)
    assert _dial(client, auth_headers).status_code == 200


def test_tagesgrenze(client, auth_headers, agent, monkeypatch) -> None:
    from backend import calls, connections, outbound

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    for _ in range(outbound.MAX_PER_DAY):
        calls.record(cid, {"direction": "out", "number": "•••567", "result": "busy"})
    r = _dial(client, auth_headers)
    assert r.status_code == 429 and r.json()["detail"]["code"] == "daily_limit"
    assert _dial(client, auth_headers).status_code == 429


def test_tagesgrenze_zaehlt_nur_ausgehende(client, auth_headers, agent) -> None:
    from backend import calls, connections, outbound

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    for _ in range(outbound.MAX_PER_DAY + 5):
        calls.record(cid, {"direction": "in", "number": "•••111", "result": "answered"})
    assert _dial(client, auth_headers).status_code == 200, "eingehende Anrufe verbrauchen kein Kontingent"


def test_tagesgrenze_zaehlt_nur_heute(client, auth_headers, agent) -> None:
    from backend import calls, connections, outbound
    from hydrahive.db.connection import db

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    for _ in range(outbound.MAX_PER_DAY):
        calls.record(cid, {"direction": "out", "number": "•••567", "result": "busy"})
    with db() as c:
        c.execute("UPDATE module_telephony_calls SET started_at='2020-01-01T00:00:00+00:00'")
    assert _dial(client, auth_headers).status_code == 200


def test_auflegen(client, auth_headers, agent) -> None:
    _setup(client, auth_headers)
    _dial(client, auth_headers)
    r = client.post(f"{BASE}/dial/hangup", headers=auth_headers)
    assert r.status_code == 200 and agent.calls[0].hung


def test_auflegen_ohne_anruf(client, auth_headers, agent) -> None:
    _setup(client, auth_headers)
    assert client.post(f"{BASE}/dial/hangup", headers=auth_headers).json() == {"active": False}


def test_nur_eigene_verbindung(client, auth_headers, other_headers, agent) -> None:
    _setup(client, auth_headers)
    assert _dial(client, other_headers).status_code == 404
    _dial(client, auth_headers)
    assert client.get(f"{BASE}/dial", headers=other_headers).json() == {"active": False}
    assert client.post(f"{BASE}/dial/hangup", headers=other_headers).json() == {"active": False}
    assert not agent.calls[0].hung


def test_fremder_nutzer_mit_eigener_verbindung_legt_nicht_meinen_anruf_auf(client, auth_headers, other_headers,
                                                                          agent) -> None:
    _setup(client, auth_headers)
    r = client.put(BASE, json={"registrar": "fritz.box", "username": "anderes-telefon", "password": "Sehr-Geheim-43",
                               "local_sip_port": 5072}, headers=other_headers)
    assert r.status_code == 200, r.text
    _dial(client, auth_headers)
    assert client.post(f"{BASE}/dial/hangup", headers=other_headers).json() == {"active": False}
    assert client.get(f"{BASE}/dial", headers=other_headers).json() == {"active": False}
    assert not agent.calls[0].hung


def test_ausgehender_anruf_schliesst_kein_testfenster(client, auth_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    assert client.post(f"{BASE}/test-call", headers=auth_headers).status_code == 200
    cid = connections._row("user:user-owner")["id"]
    calls.record(cid, {"direction": "out", "number": "•••567", "result": "answered"})
    assert client.get(BASE, headers=auth_headers).json()["test_until"] is not None, "Fenster bleibt offen"
    got = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"]
    assert got[0]["is_test"] is False


def test_unbekannte_richtung_wird_eingehend(client, auth_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    calls.record(cid, {"direction": "seitwärts", "number": "•••567", "result": "answered"})
    assert client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"][0]["direction"] == "in"


def test_anrufliste_zeigt_richtung(client, auth_headers) -> None:
    from backend import calls, connections

    _setup(client, auth_headers)
    cid = connections._row("user:user-owner")["id"]
    calls.record(cid, {"direction": "out", "number": "•••567", "result": "answered"})
    calls.record(cid, {"number": "•••111", "result": "answered"})
    got = client.get(f"{BASE}/calls", headers=auth_headers).json()["calls"]
    assert [c["direction"] for c in got] == ["in", "out"]


def test_eingaben_begrenzt(client, auth_headers, agent) -> None:
    _setup(client, auth_headers)
    assert _dial(client, auth_headers, text="x" * 501).status_code == 422
    assert _dial(client, auth_headers, number="0" * 41).status_code == 422
    assert _dial(client, auth_headers, text="a\x00b").status_code == 422
    r = client.post(f"{BASE}/dial", json={"number": "030 1234567", "extra": 1}, headers=auth_headers)
    assert r.status_code == 422


def test_ohne_anmeldung_401(client) -> None:
    assert client.post(f"{BASE}/dial", json={"number": "030 1234567"}).status_code == 401
