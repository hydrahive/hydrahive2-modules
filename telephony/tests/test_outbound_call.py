"""Ausgehender Anruf gegen die Test-Anlage (PLAN-ANRUFEN-3 Schritt 2). Echte UDP-Sockets, echte Digest-Prüfung."""
from __future__ import annotations

import socket
import threading
import time

from _fake_pbx import FakePbx
from backend.sip import message


def _wait(cond, timeout: float = 3.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


class Line:
    """SIP-Socket von HydraHive + Pumpe, die Antworten/Anfragen an den OutboundCall gibt (wie der SipAgent)."""

    def __init__(self, pbx: FakePbx, *, password: str = "Sehr-Geheim-42", ring_timeout: float = 5.0,
                 max_seconds: float = 5.0, audio_ms: int = 300, **kw) -> None:
        from backend.sip.outbound import OutboundCall

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.rtp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_sock.bind(("127.0.0.1", 0))
        self.finished: list = []
        self.call = OutboundCall(sock=self.sock, target=pbx.addr, local=self.sock.getsockname(),
                                 user="hydra-telefon", password=password, domain="fritz.box", number="0301234567",
                                 rtp_sock=self.rtp_sock, audio=lambda codec: b"\xd5" * (8 * audio_ms),
                                 ring_timeout=ring_timeout, max_seconds=max_seconds,
                                 on_finish=self.finished.append, **kw)
        self._stop = threading.Event()
        threading.Thread(target=self._pump, daemon=True).start()
        self.call.start()

    def _pump(self) -> None:
        self.sock.settimeout(0.05)
        while not self._stop.is_set():
            try:
                data, addr = self.sock.recvfrom(65535)
            except (TimeoutError, OSError):
                continue
            try:
                m = message.parse(data)
            except message.ParseError:
                continue
            if m.is_request:
                self.call.on_request(m, addr)
            else:
                self.call.on_response(m)

    def close(self) -> None:
        self._stop.set()
        self.call.hangup()
        self.call.join(3)
        self.sock.close()


def _run(pbx_kw: dict, line_kw: dict | None = None, *, wait: float = 5.0):
    pbx = FakePbx(**pbx_kw)
    line = Line(pbx, **(line_kw or {}))
    try:
        assert _wait(lambda: line.finished, wait), f"Anruf endet nicht (Zustand {line.call.state})"
        return pbx, line, line.finished[0]
    finally:
        line.close()
        pbx.close()


def _invites(pbx: FakePbx) -> list[message.Message]:
    return [r for r in pbx.requests if r.method == "INVITE"]


def test_normal_digest_klingeln_abnehmen_ansage_auflegen() -> None:
    pbx, _line, call = _run({"auth": 401, "ring": 0.2})
    inv = _invites(pbx)
    assert len(inv) == 2, "erst ohne, dann mit Anmeldung"
    assert inv[0].uri == "sip:0301234567@fritz.box" and inv[1].uri == inv[0].uri
    assert inv[0].header("call-id") == inv[1].header("call-id"), "gleiche Call-ID"
    assert inv[1].header("cseq") == "2 INVITE" and inv[1].header("authorization")
    assert "hydra-telefon@fritz.box" in (inv[0].header("from") or "") and ";tag=" in inv[0].header("from")
    assert b"m=audio" in inv[0].body and b"PCMA" in inv[0].body and b"PCMU" in inv[0].body
    acks = [r for r in pbx.requests if r.method == "ACK"]
    assert acks[0].header("cseq") == "1 ACK", "ACK auf 401 (RFC 3261 §17.1.1.3)"
    assert pbx.acked.is_set(), "ACK auf 200"
    assert ";tag=pbx1" in (acks[-1].header("to") or "")
    assert pbx.bye_received.is_set(), "HydraHive legt nach der Ansage auf"
    assert call.result == "answered" and call.rtp_out >= 10 and len(pbx.rtp_packets) >= 10
    assert call.codec == "PCMA"


def test_407_proxy_anmeldung() -> None:
    pbx, _line, call = _run({"auth": 407})
    assert _invites(pbx)[1].header("proxy-authorization") and call.result == "answered"


def test_ohne_anmeldung() -> None:
    pbx, _line, call = _run({"auth": None})
    assert len(_invites(pbx)) == 1 and call.result == "answered"


def test_falsches_kennwort_kein_dritter_versuch() -> None:
    pbx, _line, call = _run({"auth": 401}, {"password": "falsch"})
    assert call.result == "auth_failed" and len(_invites(pbx)) == 2


def test_anlage_fordert_immer_wieder_anmeldung_genau_zwei_versuche() -> None:
    """Manche Anlagen antworten bei falschem Kennwort erneut mit 401 statt 403 – nie endlos neu anmelden."""
    pbx, _line, call = _run({"auth": 401, "rechallenge": True})
    assert call.result == "auth_failed" and len(_invites(pbx)) == 2


def test_verspaetete_antwort_auf_den_ersten_versuch_wird_ignoriert() -> None:
    """Die 401 auf CSeq 1 kommt doppelt an, nachdem schon mit Anmeldung (CSeq 2) gewählt wurde."""
    pbx, _line, call = _run({"auth": 401, "repeat_challenge": True, "ring": 0.4})
    assert call.result == "answered" and len(_invites(pbx)) == 2


def test_gegenseite_legt_in_der_letzten_halben_sekunde_auf() -> None:
    """BYE kommt nach dem Ende der Ansage, während HydraHive noch 0,5 s wartet → kein eigenes BYE hinterher."""
    pbx, _line, call = _run({"hangup_after": 0.45}, {"audio_ms": 200})
    assert call.result == "remote_hangup" and not pbx.bye_received.is_set()


def test_besetzt_abgelehnt_ungueltig_fehler() -> None:
    for outcome, result in [("busy", "busy"), ("decline", "declined"), ("notfound", "invalid_number"),
                            ("fail", "failed")]:
        pbx, _line, call = _run({"outcome": outcome})
        assert call.result == result, outcome
        assert pbx.methods().count("ACK") >= 2, f"{outcome}: auch Fehlerantworten bekommen ACK"
        last_ack = [r for r in pbx.requests if r.method == "ACK"][-1]
        assert ";tag=pbx1" in (last_ack.header("to") or ""), "ACK übernimmt To mit Tag der Antwort (§17.1.1.3)"
        assert not pbx.bye_received.is_set()


def test_niemand_nimmt_ab_cancel_nach_zeitgrenze() -> None:
    pbx, _line, call = _run({"outcome": "ring"}, {"ring_timeout": 0.6})
    assert call.result == "no_answer" and pbx.cancelled.is_set()
    cancel = next(r for r in pbx.requests if r.method == "CANCEL")
    last_inv = _invites(pbx)[-1]
    assert cancel.header("via") == last_inv.header("via"), "CANCEL mit gleichem Branch wie der INVITE"
    assert cancel.header("cseq") == last_inv.header("cseq").replace("INVITE", "CANCEL")


def test_auflegen_beim_klingeln() -> None:
    pbx = FakePbx(outcome="ring")
    line = Line(pbx)
    try:
        assert _wait(lambda: line.call.state == "ringing")
        line.call.hangup()
        assert _wait(lambda: line.finished)
        assert line.finished[0].result == "cancelled" and pbx.cancelled.is_set()
    finally:
        line.close()
        pbx.close()


def test_auflegen_im_gespraech() -> None:
    pbx = FakePbx()
    line = Line(pbx, audio_ms=10000)
    try:
        assert _wait(lambda: line.call.state == "answered")
        time.sleep(0.2)
        line.call.hangup()
        assert _wait(lambda: line.finished)
        assert line.finished[0].result == "hung_up" and pbx.bye_received.is_set()
    finally:
        line.close()
        pbx.close()


def test_gegenseite_legt_auf() -> None:
    pbx, _line, call = _run({"hangup_after": 0.3}, {"audio_ms": 10000})
    assert call.result == "remote_hangup"
    assert not pbx.bye_received.is_set(), "kein eigenes BYE, wenn die Gegenseite schon aufgelegt hat"


def test_wiederholtes_200_bekommt_wieder_ack() -> None:
    pbx, _line, call = _run({"repeat_ok": True}, {"audio_ms": 1200})
    oks = [r for r in pbx.requests if r.method == "ACK" and r.header("cseq") == "2 ACK"]
    assert len(oks) >= 2 and call.result == "answered"


def test_anlage_antwortet_nicht() -> None:
    pbx, _line, call = _run({"outcome": "silent"}, {"invite_timeout": 1.0})
    assert call.result == "unreachable" and len(_invites(pbx)) >= 2, "INVITE wird wiederholt"


def test_kein_gemeinsamer_codec() -> None:
    pbx, _line, call = _run({"codecs": "9"})
    assert call.result == "codec" and pbx.acked.is_set() and pbx.bye_received.is_set()


def test_ton_von_fremder_adresse_zaehlt_nicht() -> None:
    _pbx, _line, call = _run({"wrong_rtp_source": True}, {"audio_ms": 600})
    assert call.rtp_in == 0


def test_ton_der_gegenseite_wird_gezaehlt() -> None:
    _pbx, _line, call = _run({}, {"audio_ms": 600})
    assert call.rtp_in >= 5


def test_nummer_mit_steuerzeichen_wird_nie_gesendet() -> None:
    from backend.sip.outbound import OutboundCall

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for bad in ["030;x", "030 123", "030\r\nVia: x", "sip:a@b", ""]:
            try:
                OutboundCall(sock=s, target=("127.0.0.1", 9), local=("127.0.0.1", 1), user="u", password="p",
                             domain="fritz.box", number=bad, rtp_sock=s, audio=lambda c: b"", on_finish=print)
            except ValueError:
                continue
            raise AssertionError(f"{bad!r} angenommen")
    finally:
        s.close()
