"""Wählen über die laufende Anmeldung (PLAN-ANRUFEN-3 Schritt 3): gleicher Socket, belegt in beide Richtungen."""
from __future__ import annotations

import time

import pytest
from _fake_pbx import FakePbx


def _wait(cond, timeout: float = 4.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


def _agent(pbx: FakePbx, records: list, **kw):
    from backend.sip.agent import SipAgent

    a = SipAgent(connection_id="c1", user="hydra-telefon", password="Sehr-Geheim-42", domain="fritz.box",
                 target=pbx.addr, bind=("127.0.0.1", 0), display_name="HydraHive", interval=300,
                 call_policy=lambda: "Hallo", call_record=records.append, rtp_ports=(33000, 33020),
                 call_options={"ring_seconds": 0.0, "ack_timeout": 1.0, "greeting": lambda t, c: b"\x11" * 800}, **kw)
    a.start()
    assert _wait(lambda: a.status == "registered")
    return a


@pytest.fixture
def pbx():
    p = FakePbx(ring=0.1)
    yield p
    p.close()


def test_waehlt_ueber_den_socket_der_anmeldung(pbx) -> None:
    records: list = []
    a = _agent(pbx, records)
    try:
        call = a.dial("0301234567", lambda codec: b"\xd5" * 1600)
        assert _wait(lambda: records, timeout=6)
        inv = [r for r in pbx.requests if r.method == "INVITE"]
        assert inv and pbx.peer == a.local_addr, "derselbe Port wie die Anmeldung"
        assert records[0]["direction"] == "out" and records[0]["result"] == "answered"
        assert records[0]["number"] == "•••567", "nur maskiert"
        assert call.result == "answered" and a.status == "registered"
    finally:
        a.stop()


def test_nur_wenn_angemeldet() -> None:
    from backend.sip.agent import NotReady, SipAgent

    a = SipAgent(connection_id="c1", user="u", password="p", domain="fritz.box", target=("127.0.0.1", 9),
                 bind=("127.0.0.1", 0), display_name="H", interval=300)
    with pytest.raises(NotReady):
        a.dial("0301234567", lambda c: b"")


def test_zweiter_anruf_raus_waehrend_einer_laeuft(pbx) -> None:
    from backend.sip.agent import LineBusy

    pbx.outcome = "ring"
    records: list = []
    a = _agent(pbx, records)
    try:
        first = a.dial("0301234567", lambda c: b"")
        assert _wait(lambda: first.state == "ringing")
        with pytest.raises(LineBusy):
            a.dial("0301234568", lambda c: b"")
        first.hangup()
        assert _wait(lambda: records and records[0]["result"] == "cancelled")
    finally:
        a.stop()


def test_eingehend_waehrend_ausgehend_ist_besetzt(pbx) -> None:
    pbx.outcome = "ring"
    records: list = []
    a = _agent(pbx, records)
    try:
        call = a.dial("0301234567", lambda c: b"")
        assert _wait(lambda: call.state == "ringing")
        pbx.invite_in(a.local_addr, "in-1")
        assert _wait(lambda: any(r.status == 486 for r in pbx.responses_for("in-1")))
        call.hangup()
    finally:
        a.stop()


def test_ausgehend_waehrend_eingehend_ist_belegt(pbx) -> None:
    from backend.sip.agent import LineBusy

    records: list = []
    a = _agent(pbx, records, )
    a.calls._ring = 2.0                                     # eingehender Anruf klingelt noch
    try:
        pbx.invite_in(a.local_addr, "in-2")
        assert _wait(lambda: any(r.status == 180 for r in pbx.responses_for("in-2")))
        with pytest.raises(LineBusy):
            a.dial("0301234567", lambda c: b"")
    finally:
        a.stop()


def test_stop_legt_ausgehend_auf(pbx) -> None:
    pbx.outcome = "ring"
    records: list = []
    a = _agent(pbx, records)
    call = a.dial("0301234567", lambda c: b"")
    assert _wait(lambda: call.state == "ringing")
    a.stop()
    assert _wait(lambda: not call.alive, timeout=10) and pbx.cancelled.is_set()


def test_antworten_anderer_anrufe_gehen_nicht_an_den_ausgehenden(pbx) -> None:
    """Die Antwort auf das REGISTER (andere Call-ID) darf den ausgehenden Anruf nicht stören."""
    records: list = []
    a = _agent(pbx, records)
    try:
        call = a.dial("0301234567", lambda codec: b"\xd5" * 800)
        assert _wait(lambda: records, timeout=6) and call.result == "answered"
    finally:
        a.stop()


class _Alive:
    def __init__(self, cid: str, alive: bool = True) -> None:
        self.call_id, self.alive = cid, alive


def test_dispatcher_eintragen_nur_bei_freier_leitung() -> None:
    from backend.sip.dispatch import CallDispatcher

    d = CallDispatcher(policy=lambda: None, rtp_ports=(34000, 34010), record=lambda r: None)
    assert not d.busy()
    assert d.add_outbound(_Alive("a"))
    assert d.busy()
    assert not d.add_outbound(_Alive("b")), "zweiter Anruf raus"
    d.finish_outbound(_Alive("a"))
    assert not d.busy() and d.add_outbound(_Alive("c"))
    d.finish_outbound(_Alive("c"))
    d._calls["in"] = _Alive("in")
    assert d.busy() and not d.add_outbound(_Alive("d")), "eingehender Anruf läuft"
    d._calls["in"] = _Alive("in", alive=False)
    assert not d.busy() and d.add_outbound(_Alive("e")), "beendete Anrufe zählen nicht"
