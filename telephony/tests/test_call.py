"""Eingehender Anruf: abnehmen, Ansage, auflegen – gegen einen echten Test-Anrufer (PLAN-ANRUFE-2A Schritt 5)."""
from __future__ import annotations

import socket
import threading
import time

import pytest
from _fake_caller import FakeCaller


def _wait(cond, timeout: float = 4.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


class Hydra:
    """SIP-Socket von HydraHive + Pumpe, die alles an den CallDispatcher gibt (wie der SipAgent)."""

    def __init__(self, **kw) -> None:
        from backend.sip.dispatch import CallDispatcher

        self.records: list[dict] = []
        self.texts: list[str] = []
        self.answer = kw.pop("answer", "Hallo")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.addr = self.sock.getsockname()
        defaults = {"ring_seconds": 0.0, "ack_timeout": 1.0, "max_seconds": 5}
        defaults.update(kw)
        self.d = CallDispatcher(policy=lambda: self.answer, rtp_ports=(31000, 31040), record=self.records.append,
                                greeting=self._greeting, **defaults)
        self._stop = threading.Event()
        threading.Thread(target=self._pump, daemon=True).start()

    def _greeting(self, text: str, codec: str) -> bytes:
        self.texts.append(text)
        return b"\x11" * 160 * 5                               # 100 ms „Ansage“

    def _pump(self) -> None:
        from backend.sip import message

        self.sock.settimeout(0.05)
        while not self._stop.is_set():
            try:
                data, addr = self.sock.recvfrom(65535)
            except (TimeoutError, OSError):
                continue
            m = message.parse(data)
            if m.is_request:
                self.d.handle_request(self.sock, m, addr, "127.0.0.1")
            else:
                self.d.handle_response(m)

    def close(self) -> None:
        self.d.hangup_all()
        self._stop.set()
        self.sock.close()


@pytest.fixture
def hydra():
    h = Hydra()
    yield h
    h.close()


@pytest.fixture
def caller():
    c = FakeCaller()
    yield c
    c.close()


def test_normaler_anruf_ansage_dann_auflegen(hydra, caller) -> None:
    caller.invite(hydra.addr)
    assert _wait(lambda: hydra.records), "Anruf abgeschlossen"
    st = caller.statuses()
    assert st[:3] == [100, 180, 200]
    ok = caller.responses[2]
    assert ok.header("content-type") == "application/sdp" and b"m=audio 310" in ok.body
    assert b"a=rtpmap:8 PCMA/8000" in ok.body and "<sip:" in (ok.header("contact") or "")
    assert ok.header("to").endswith(";tag=" + caller.to_tag())
    assert [r.method for r in caller.requests] == ["BYE"], "HydraHive legt selbst auf"
    bye = caller.requests[0]
    assert bye.header("call-id") == caller.call_id and bye.header("to").startswith("<sip:0301234567@fritz.box>;tag=fritz1")
    assert len(caller.rtp_packets) == 5 and {p.payload_type for p in caller.rtp_packets} == {8}
    rec = hydra.records[0]
    assert rec["result"] == "answered" and rec["codec"] == "PCMA" and rec["rtp_out"] == 5
    assert rec["number"] == "•••567" and "0301234567" not in str(rec)
    assert rec["rtp_in"] >= 1, "Ton vom Anrufer kam an (nur gezählt)"
    assert hydra.texts == ["Hallo"]


def test_pcmu_wenn_anlage_es_zuerst_anbietet(hydra) -> None:
    c = FakeCaller(codecs="0 8")
    try:
        c.invite(hydra.addr)
        assert _wait(lambda: hydra.records)
        assert hydra.records[0]["codec"] == "PCMU" and {p.payload_type for p in c.rtp_packets} == {0}
    finally:
        c.close()


def test_schalter_aus_480_wie_bisher(caller) -> None:
    h = Hydra(answer=None)
    try:
        caller.invite(h.addr)
        assert _wait(lambda: 480 in caller.statuses())
        assert 200 not in caller.statuses() and h.records[0]["result"] == "rejected"
    finally:
        h.close()


def test_kein_gemeinsamer_codec_488(hydra) -> None:
    c = FakeCaller(codecs="9 101")
    try:
        c.invite(hydra.addr)
        assert _wait(lambda: 488 in c.statuses())
        assert hydra.records[0]["result"] == "codec"
    finally:
        c.close()


def test_kaputtes_sdp_488(hydra, caller) -> None:
    caller.invite(hydra.addr, body=b"Unsinn")
    assert _wait(lambda: 488 in caller.statuses())


def test_anrufer_legt_waehrend_klingeln_auf_cancel(caller) -> None:
    h = Hydra(ring_seconds=2.0)
    try:
        caller.invite(h.addr)
        assert _wait(lambda: 180 in caller.statuses())
        caller.cancel()
        assert _wait(lambda: h.records)
        assert 487 in caller.statuses() and 200 not in [r.status for r in caller.responses
                                                          if "INVITE" in r.header("cseq")]
        assert h.records[0]["result"] == "cancelled" and caller.rtp_packets == []
    finally:
        h.close()


def test_anrufer_legt_waehrend_ansage_auf(caller) -> None:
    h = Hydra()
    h._greeting = lambda text, codec: b"\x11" * 160 * 200        # 4 s Ansage
    h.d._greeting = h._greeting
    try:
        caller.invite(h.addr)
        assert _wait(lambda: len(caller.rtp_packets) >= 3)
        caller.bye()
        assert _wait(lambda: h.records)
        assert h.records[0]["result"] == "caller_hangup" and h.records[0]["rtp_out"] < 100
        assert any(r.status == 200 and "BYE" in r.header("cseq") for r in caller.responses)
        assert "BYE" not in [r.method for r in caller.requests]
    finally:
        h.close()


def test_kein_ack_dann_aufgeben(hydra) -> None:
    c = FakeCaller(auto_ack=False)
    try:
        c.invite(hydra.addr)
        assert _wait(lambda: hydra.records, timeout=5)
        assert hydra.records[0]["result"] == "no_ack"
        assert c.statuses().count(200) >= 2, "200 OK wird bis zum ACK wiederholt"
        assert c.rtp_packets == []
    finally:
        c.close()


def test_zweiter_anruf_gleichzeitig_besetzt(caller) -> None:
    h = Hydra(ring_seconds=1.5)
    other = FakeCaller()
    try:
        caller.invite(h.addr)
        assert _wait(lambda: 180 in caller.statuses())
        other.invite(h.addr)
        assert _wait(lambda: 486 in other.statuses())
        assert _wait(lambda: len(h.records) == 2, timeout=6)
        assert sorted(r["result"] for r in h.records) == ["answered", "busy"]
    finally:
        other.close()
        h.close()


def test_wiederholter_invite_startet_keinen_zweiten_anruf(caller) -> None:
    h = Hydra(ring_seconds=1.0)
    try:
        caller.invite(h.addr)
        assert _wait(lambda: 180 in caller.statuses())
        before = caller.statuses().count(180)
        caller.invite(h.addr)                                    # gleiche Call-ID = Wiederholung
        assert _wait(lambda: caller.statuses().count(180) > before, timeout=1), "letzte Antwort wird wiederholt"
        assert _wait(lambda: h.records, timeout=6)
        assert len(h.records) == 1 and 486 not in caller.statuses()
    finally:
        h.close()


def test_hoechstdauer_begrenzt_die_ansage(caller) -> None:
    h = Hydra(max_seconds=0.1)
    h.d._greeting = lambda text, codec: b"\x11" * 8000 * 10
    try:
        caller.invite(h.addr)
        assert _wait(lambda: h.records, timeout=6)
        assert h.records[0]["rtp_out"] <= 6
    finally:
        h.close()


def test_rtp_von_fremder_adresse_zaehlt_nicht(hydra) -> None:
    """Nur Ton von der Adresse aus dem SDP der Anlage wird gezählt (der Rest wird verworfen)."""
    from backend.sip import message

    c = FakeCaller(send_rtp=False)
    evil = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        hydra.d._greeting = lambda text, codec: b"\x11" * 160 * 25
        c.invite(hydra.addr, body=c.sdp().replace(b"c=IN IP4 127.0.0.1", b"c=IN IP4 127.0.0.2"))
        assert _wait(lambda: 200 in c.statuses())
        ok = next(r for r in c.responses if r.status == 200)
        port = int(ok.body.split(b"m=audio ")[1].split(b" ")[0])
        for _ in range(5):
            evil.sendto(b"\x80\x08" + b"\x00" * 170, ("127.0.0.1", port))
        assert _wait(lambda: hydra.records, timeout=6)
        assert hydra.records[0]["rtp_in"] == 0
        del message
    finally:
        evil.close()
        c.close()


def test_bye_fuer_unbekannten_anruf_481(hydra, caller) -> None:
    caller.target = hydra.addr
    caller.bye()
    assert _wait(lambda: 481 in caller.statuses())


@pytest.mark.parametrize("from_hdr,masked", [
    ("<sip:061099669981@fritz.box>;tag=x", "•••981"), ('"Max" <sip:+4930123456@x>;tag=y', "•••456"),
    ("<sip:anonymous@anonymous.invalid>;tag=z", "unbekannt"), ("<sip:12@x>", "unbekannt"), ("kaputt", "unbekannt"),
])
def test_rufnummer_maskiert(from_hdr: str, masked: str) -> None:
    from backend.sip.dispatch import mask_number

    assert mask_number(from_hdr) == masked
