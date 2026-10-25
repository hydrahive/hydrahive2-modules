"""Test-Anlage für ausgehende Anrufe: verhält sich wie die FRITZ!Box, wenn HydraHive wählt (PLAN-ANRUFEN-3).

INVITE von HydraHive → (optional) 401/407 mit Digest-Prüfung gegen das bekannte Kennwort → 100 → 180 → nach
``ring`` Sekunden je nach ``outcome``:
- ``answer``  – 200 OK mit SDP (eigener RTP-Port), wartet auf ACK, zählt RTP; ``hangup_after`` s → BYE von der Anlage
- ``busy`` / ``decline`` / ``notfound`` / ``fail`` – 486 / 603 / 404 / 500
- ``ring``    – klingelt ewig (für CANCEL/Zeitgrenze)
- ``silent``  – antwortet gar nicht
Beantwortet CANCEL (200 + 487), BYE (200), zeichnet alles auf.
"""
from __future__ import annotations

import hashlib
import re
import socket
import threading
import time

from backend.media import rtp
from backend.sip import message


class FakePbx:
    def __init__(self, *, user: str = "hydra-telefon", password: str = "Sehr-Geheim-42", realm: str = "fritz.box",
                 auth: int | None = 401, outcome: str = "answer", ring: float = 0.1, hangup_after: float | None = None,
                 codecs: str = "8 0", repeat_ok: bool = False, wrong_rtp_source: bool = False,
                 rechallenge: bool = False, repeat_challenge: bool = False) -> None:
        self.user, self.password, self.realm, self.auth = user, password, realm, auth
        self.outcome, self.ring, self.hangup_after, self.codecs = outcome, ring, hangup_after, codecs
        self.repeat_ok, self.wrong_rtp_source = repeat_ok, wrong_rtp_source
        self.rechallenge, self.repeat_challenge = rechallenge, repeat_challenge   # falsches Kennwort / 401 doppelt
        self.sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sip.bind(("127.0.0.1", 0))
        self.rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp.bind(("127.0.0.1", 0))
        self.addr = self.sip.getsockname()
        self.requests: list[message.Message] = []
        self.all: list[message.Message] = []
        self.rtp_packets: list[rtp.RtpHeader] = []
        self.answered_invite: message.Message | None = None
        self.peer: tuple[str, int] | None = None
        self.acked = threading.Event()
        self.cancelled = threading.Event()
        self.bye_received = threading.Event()
        self._stop = threading.Event()
        self._pending: dict[str, message.Message] = {}
        for target in (self._sip_loop, self._rtp_loop):
            threading.Thread(target=target, daemon=True).start()

    def close(self) -> None:
        self._stop.set()
        self.sip.close()
        self.rtp.close()

    def methods(self) -> list[str]:
        return [r.method for r in self.requests if r.method != "REGISTER"]

    def invite_in(self, target: tuple[str, int], call_id: str = "inbound-1") -> None:
        """Die Anlage ruft HydraHive an (für „Leitung belegt“)."""
        body = (f"v=0\r\nc=IN IP4 127.0.0.1\r\nm=audio {self.rtp.getsockname()[1]} RTP/AVP 8\r\n"
                "a=rtpmap:8 PCMA/8000\r\n").encode()
        self._send(message.build_request("INVITE", "sip:hydra-telefon@127.0.0.1", [
            ("Via", f"SIP/2.0/UDP {self.addr[0]}:{self.addr[1]};branch=z9hG4bKin{call_id}"),
            ("From", "<sip:0301234567@fritz.box>;tag=in"), ("To", "<sip:hydra-telefon@fritz.box>"),
            ("Call-ID", call_id), ("CSeq", "1 INVITE"), ("Contact", f"<sip:fritz@{self.addr[0]}:{self.addr[1]}>"),
            ("Content-Type", "application/sdp")], body), target)

    def responses_for(self, call_id: str) -> list[message.Message]:
        return [r for r in self.all if not r.is_request and r.header("call-id") == call_id]

    # ---- SIP ----
    def _send(self, raw: bytes, addr) -> None:
        try:
            self.sip.sendto(raw, addr)
        except OSError:
            pass

    def _resp(self, req, code, reason, *, tag=True, extra=(), body=b"") -> bytes:
        return message.build_response(req, code, reason, to_tag="pbx1" if tag else None, extra=list(extra), body=body)

    def _digest_ok(self, value: str, req: message.Message) -> bool:
        p = dict(re.findall(r'(\w+)="?([^",]+)"?', value))
        ha1 = hashlib.md5(f"{self.user}:{self.realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"INVITE:{p.get('uri')}".encode()).hexdigest()
        want = hashlib.md5(f"{ha1}:{p.get('nonce')}:{ha2}".encode()).hexdigest()
        return p.get("username") == self.user and p.get("response") == want

    def _sip_loop(self) -> None:
        self.sip.settimeout(0.05)
        while not self._stop.is_set():
            try:
                data, addr = self.sip.recvfrom(65535)
            except (TimeoutError, OSError):
                continue
            try:
                m = message.parse(data)
            except message.ParseError:
                continue
            self.all.append(m)
            if not m.is_request:
                continue
            self.requests.append(m)
            self.peer = addr
            if self.outcome == "silent":
                continue
            if m.method == "REGISTER":                                 # Anmeldung ohne Prüfung (für SipAgent-Tests)
                self._send(self._resp(m, 200, "OK", extra=[("Contact", f"{m.header('contact')};expires=300")]), addr)
            elif m.method == "INVITE":
                self._invite(m, addr)
            elif m.method == "ACK":
                if self.answered_invite is not None and (m.header("cseq") or "").split()[0] == \
                        (self.answered_invite.header("cseq") or "").split()[0]:
                    self.acked.set()
            elif m.method == "CANCEL":
                self._send(self._resp(m, 200, "OK", tag=False), addr)
                inv = self._pending.pop(m.header("call-id") or "", None)
                if inv is not None:
                    self.cancelled.set()
                    self._send(self._resp(inv, 487, "Request Terminated"), addr)
            elif m.method == "BYE":
                self.bye_received.set()
                self._send(self._resp(m, 200, "OK"), addr)

    def _invite(self, m: message.Message, addr) -> None:
        hdr = "authorization" if self.auth == 401 else "proxy-authorization"
        if self.auth and (self.rechallenge or not (m.header(hdr) and self._digest_ok(m.header(hdr), m))):
            if m.header(hdr) and not self.rechallenge:
                self._send(self._resp(m, 403, "Forbidden"), addr)
                return
            name = "WWW-Authenticate" if self.auth == 401 else "Proxy-Authenticate"
            challenge = self._resp(m, self.auth, "Unauthorized", extra=[
                (name, f'Digest realm="{self.realm}", nonce="n{len(self.requests)}", algorithm=MD5')])
            self._send(challenge, addr)
            if self.repeat_challenge and not m.header(hdr):
                threading.Timer(0.15, self._send, args=(challenge, addr)).start()   # verspätete Wiederholung
            return
        self._send(self._resp(m, 100, "Trying", tag=False), addr)
        self._pending[m.header("call-id") or ""] = m
        threading.Thread(target=self._progress, args=(m, addr), daemon=True).start()

    def _progress(self, m: message.Message, addr) -> None:
        self._send(self._resp(m, 180, "Ringing"), addr)
        if self.outcome == "ring":
            return
        time.sleep(self.ring)
        if (m.header("call-id") or "") not in self._pending:
            return                                                    # inzwischen CANCEL
        self._pending.pop(m.header("call-id") or "", None)
        codes = {"busy": (486, "Busy Here"), "decline": (603, "Decline"), "notfound": (404, "Not Found"),
                 "fail": (500, "Server Error")}
        if self.outcome in codes:
            self._send(self._resp(m, *codes[self.outcome]), addr)
            return
        body = (f"v=0\r\no=fritz 1 1 IN IP4 127.0.0.1\r\ns=call\r\nc=IN IP4 127.0.0.1\r\nt=0 0\r\n"
                f"m=audio {self.rtp.getsockname()[1]} RTP/AVP {self.codecs}\r\na=rtpmap:8 PCMA/8000\r\n"
                f"a=rtpmap:0 PCMU/8000\r\na=rtpmap:9 G722/8000\r\na=sendrecv\r\n").encode()
        ok = self._resp(m, 200, "OK", extra=[("Contact", f"<sip:fritz@{self.addr[0]}:{self.addr[1]}>"),
                                             ("Content-Type", "application/sdp")], body=body)
        self.answered_invite = m
        self._send(ok, addr)
        if self.repeat_ok:
            time.sleep(0.6)
            self._send(ok, addr)
        threading.Thread(target=self._talk, args=(m,), daemon=True).start()
        if self.hangup_after is not None:
            time.sleep(self.hangup_after)
            self._bye(m, addr)

    def _talk(self, invite: message.Message) -> None:
        from backend.sip import sdp

        try:
            o = sdp.parse_offer(invite.body)
        except sdp.SdpError:
            return
        sender = self.rtp
        if self.wrong_rtp_source:
            sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender.bind(("127.0.0.2", 0))
        for i in range(10):
            try:
                sender.sendto(rtp.packet(payload_type=8, seq=i, timestamp=i * 160, ssrc=7, payload=b"\xd5" * 160),
                              (o.address, o.port))
            except OSError:
                return
            time.sleep(0.02)

    def _bye(self, invite: message.Message, addr) -> None:
        contact = (invite.header("contact") or "").strip("<>").split(">")[0]
        frm = invite.header("from") or ""
        raw = message.build_request("BYE", contact or "sip:hydra@x", [
            ("Via", f"SIP/2.0/UDP {self.addr[0]}:{self.addr[1]};branch=z9hG4bKpbxbye"),
            ("From", f"{invite.header('to')};tag=pbx1"), ("To", frm), ("Call-ID", invite.header("call-id") or ""),
            ("CSeq", "1 BYE"), ("Max-Forwards", "70")])
        self._send(raw, addr)

    def _rtp_loop(self) -> None:
        self.rtp.settimeout(0.05)
        while not self._stop.is_set():
            try:
                data, _ = self.rtp.recvfrom(2048)
            except (TimeoutError, OSError):
                continue
            p = rtp.parse(data)
            if p:
                self.rtp_packets.append(p)
