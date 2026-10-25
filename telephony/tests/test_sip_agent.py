"""Dauerverbindung: anmelden, erneuern, Anfragen beantworten, abmelden (PLAN-EINSTELLUNGEN Schritt 5)."""
from __future__ import annotations

import socket
import time

import pytest
from _fake_registrar import FakeRegistrar


def _wait(cond, timeout: float = 4.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


def _cfg(reg: FakeRegistrar, **over) -> dict:
    d = {"connection_id": "c1", "user": "hydra-telefon", "password": "Sehr-Geheim-42", "domain": "fritz.box",
         "target": ("127.0.0.1", reg.port), "bind": ("127.0.0.1", 0), "display_name": "HydraHive", "interval": 300}
    d.update(over)
    return d


@pytest.fixture
def reg():
    r = FakeRegistrar()
    yield r
    r.close()


def test_verbindet_und_meldet_status(reg) -> None:
    from backend.sip.agent import SipAgent

    states = []
    a = SipAgent(**_cfg(reg), on_status=lambda code: states.append(code))
    a.start()
    try:
        assert _wait(lambda: a.status == "registered")
        assert states[:2] == ["connecting", "registered"]
    finally:
        a.stop()
    assert a.status == "disconnected"
    assert reg.registers()[-1].header("expires") == "0", "beim Trennen abgemeldet"


def test_erneuert_vor_ablauf(reg) -> None:
    from backend.sip.agent import SipAgent

    r = FakeRegistrar(max_expires=2)
    a = SipAgent(**_cfg(r, interval=60))
    a.start()
    try:
        assert _wait(lambda: a.status == "registered")
        first = len(r.registers())
        # Ablauf 2 s → Erneuerung nach ~1 s (Hälfte); zwei Erneuerungen (je 2 REGISTER) in < 3 s
        assert _wait(lambda: len(r.registers()) >= first + 4, timeout=2.9), "erneuert bei ~Hälfte der Ablaufzeit"
        assert a.status == "registered"
    finally:
        a.stop()
        r.close()


def test_falsches_kennwort_bleibt_haengen_ohne_dauerfeuer(reg) -> None:
    from backend.sip.agent import SipAgent

    a = SipAgent(**_cfg(reg, password="Falsch-Falsch-1"), retry_delays=(0.1, 0.1))
    a.start()
    try:
        assert _wait(lambda: a.status == "auth_failed")
        n = len(reg.registers())
        time.sleep(1.0)
        assert len(reg.registers()) == n, "bei falschem Kennwort nicht ständig neu versuchen (Sperre der FRITZ!Box)"
    finally:
        a.stop()


def test_nicht_erreichbar_versucht_spaeter_erneut() -> None:
    from backend.sip.agent import SipAgent

    r = FakeRegistrar(silent=True)
    a = SipAgent(**_cfg(r), register_timeout=0.6, retry_delays=(0.3, 0.3))
    a.start()
    try:
        assert _wait(lambda: a.status == "unreachable")
        r.silent = False
        assert _wait(lambda: a.status == "registered", timeout=5)
    finally:
        a.stop()
        r.close()


def test_port_belegt() -> None:
    from backend.sip.agent import SipAgent

    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    blocker.bind(("127.0.0.1", 0))
    r = FakeRegistrar()
    try:
        a = SipAgent(**_cfg(r, bind=blocker.getsockname()))
        a.start()
        assert _wait(lambda: a.status == "port_in_use")
        a.stop()
        assert r.registers() == []
    finally:
        blocker.close()
        r.close()


def _req(method: str, call_id: str) -> bytes:
    from backend.sip import message

    return message.build_request(method, "sip:hydra-telefon@127.0.0.1", [
        ("Via", "SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK" + call_id), ("From", "<sip:030123@fritz.box>;tag=a"),
        ("To", "<sip:hydra-telefon@fritz.box>"), ("Call-ID", call_id), ("CSeq", f"1 {method}")])


def _answers(reg: FakeRegistrar, call_id: str):
    return [m for m in reg.requests if not m.is_request and m.header("call-id") == call_id]


def test_eingehender_anruf_wird_mit_480_abgelehnt(reg) -> None:
    """Etappe 1: Anrufe noch nicht annehmen – höflich ablehnen, andere Telefone klingeln weiter."""
    from backend.sip.agent import SipAgent

    a = SipAgent(**_cfg(reg))
    a.start()
    try:
        assert _wait(lambda: a.status == "registered")
        reg.send(_req("INVITE", "inv-1"), a.local_addr)
        assert _wait(lambda: any(m.status == 480 for m in _answers(reg, "inv-1")))
        assert ";tag=" in _answers(reg, "inv-1")[-1].header("to")
        reg.send(_req("ACK", "inv-1"), a.local_addr)
        reg.send(_req("OPTIONS", "opt-1"), a.local_addr)
        assert _wait(lambda: any(m.status == 200 for m in _answers(reg, "opt-1")))
        assert a.status == "registered"
    finally:
        a.stop()


def test_anfragen_fremder_absender_werden_ignoriert(reg) -> None:
    from backend.sip.agent import SipAgent

    a = SipAgent(**_cfg(reg))
    a.start()
    evil = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    evil.bind(("127.0.0.1", 0))
    evil.settimeout(0.5)
    try:
        assert _wait(lambda: a.status == "registered")
        evil.sendto(_req("OPTIONS", "opt-evil"), a.local_addr)
        with pytest.raises((TimeoutError, socket.timeout)):
            evil.recvfrom(65535)
    finally:
        evil.close()
        a.stop()


def test_stop_ist_schnell_und_mehrfach_sicher(reg) -> None:
    from backend.sip.agent import SipAgent

    a = SipAgent(**_cfg(reg))
    a.start()
    assert _wait(lambda: a.status == "registered")
    t = time.monotonic()
    a.stop()
    a.stop()
    assert time.monotonic() - t < 3
    assert not a.alive


def test_kennwort_nicht_in_repr(reg) -> None:
    from backend.sip.agent import SipAgent

    assert "Sehr-Geheim-42" not in repr(SipAgent(**_cfg(reg)))


def test_gebunden_an_alle_adressen_meldet_die_echte_quelladresse(reg) -> None:
    """Bind 0.0.0.0 → in Via/Contact steht die Adresse, über die die Anlage erreicht wird (nie 0.0.0.0)."""
    from backend.sip.agent import SipAgent

    a = SipAgent(**_cfg(reg, bind=("0.0.0.0", 0)))
    a.start()
    try:
        assert _wait(lambda: a.status == "registered")
        first = reg.registers()[0]
        assert "0.0.0.0" not in first.header("via") and "0.0.0.0" not in first.header("contact")
        assert "SIP/2.0/UDP 127.0.0.1:" in first.header("via")
        assert "@127.0.0.1:" in first.header("contact")
    finally:
        a.stop()


def test_quelladresse_ermitteln() -> None:
    from backend.sip.agent import source_ip_for

    assert source_ip_for(("127.0.0.1", 5060)) == "127.0.0.1"


def test_mit_anrufannahme_nimmt_ab_und_spielt_ansage(reg) -> None:
    """Die Anlage (Registrar-Socket) schickt INVITE mit SDP; HydraHive nimmt ab, spielt, legt auf."""
    from backend.media import rtp as rtpmod
    from backend.sip import message
    from backend.sip.agent import SipAgent

    records = []
    a = SipAgent(**_cfg(reg), call_policy=lambda: "Hallo", call_record=records.append, rtp_ports=(32000, 32020),
                 call_options={"ring_seconds": 0.0, "ack_timeout": 1.0, "greeting": lambda t, c: b"\x11" * 800})
    a.start()
    media = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    media.bind(("127.0.0.1", 0))
    media.settimeout(2)
    try:
        assert _wait(lambda: a.status == "registered")
        body = (f"v=0\r\nc=IN IP4 127.0.0.1\r\nm=audio {media.getsockname()[1]} RTP/AVP 8\r\n"
                "a=rtpmap:8 PCMA/8000\r\n").encode()
        reg.send(message.build_request("INVITE", "sip:hydra-telefon@127.0.0.1", [
            ("Via", f"SIP/2.0/UDP 127.0.0.1:{reg.port};branch=z9hG4bKcall"), ("From", "<sip:0301234567@fritz.box>;tag=f"),
            ("To", "<sip:hydra-telefon@fritz.box>"), ("Call-ID", "call-live"), ("CSeq", "1 INVITE"),
            ("Contact", f"<sip:fritz@127.0.0.1:{reg.port}>"), ("Content-Type", "application/sdp")], body), a.local_addr)
        assert _wait(lambda: any(m.status == 200 for m in _answers(reg, "call-live")))
        ok = next(m for m in _answers(reg, "call-live") if m.status == 200)
        reg.send(message.build_request("ACK", "sip:x", [
            ("Via", f"SIP/2.0/UDP 127.0.0.1:{reg.port};branch=z9hG4bKack"), ("From", "<sip:0301234567@fritz.box>;tag=f"),
            ("To", ok.header("to")), ("Call-ID", "call-live"), ("CSeq", "1 ACK")]), a.local_addr)
        got = [rtpmod.parse(media.recvfrom(2048)[0]) for _ in range(5)]
        assert {p.payload_type for p in got} == {8}
        assert _wait(lambda: any(m.is_request and m.method == "BYE" for m in reg.requests), timeout=4)
        assert _wait(lambda: records, timeout=6) and records[0]["result"] in ("answered", "hung_up")
        assert a.status == "registered", "Anmeldung bleibt bestehen"
    finally:
        media.close()
        a.stop()


def test_ohne_anrufannahme_480_wie_bisher(reg) -> None:
    from backend.sip.agent import SipAgent

    a = SipAgent(**_cfg(reg), call_policy=lambda: None, call_record=lambda r: None)
    a.start()
    try:
        assert _wait(lambda: a.status == "registered")
        reg.send(_req("INVITE", "inv-off"), a.local_addr)
        assert _wait(lambda: any(m.status == 480 for m in _answers(reg, "inv-off")))
    finally:
        a.stop()
