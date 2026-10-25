"""Ein ausgehender Anruf: wählen, klingeln lassen, Ansage nach dem Abnehmen, auflegen (PLAN-ANRUFEN-3).

INVITE an ``sip:<nummer>@<anlage>`` über den Socket der Anmeldung → 401/407 → ACK, INVITE mit Digest → 1xx → 200 →
ACK → Ansage als RTP → BYE. Auflegen beim Klingeln bzw. Zeitgrenze → CANCEL. Fehlerantworten bekommen ein ACK
(RFC 3261 §17.1.1.3). Ton der Gegenseite wird nur gezählt (nur von der Adresse aus deren SDP), nie gespeichert.
"""
from __future__ import annotations

import os
import queue
import socket
import threading
import time
from collections.abc import Callable

from ..media import g711, rtp
from . import digest, message, sdp

_T1, _T2 = 0.5, 4.0
_FINAL = {486: "busy", 600: "busy", 603: "declined", 404: "invalid_number", 484: "invalid_number",
          480: "no_answer", 408: "no_answer", 403: "auth_failed"}


def _tag(header: str | None) -> str:
    return (header or "").split(";tag=")[1].split(";")[0] if ";tag=" in (header or "") else ""


class OutboundCall:
    def __init__(self, *, sock: socket.socket, target: tuple[str, int], local: tuple[str, int], user: str,
                 password: str, domain: str, number: str, rtp_sock: socket.socket, audio: Callable[[str], bytes],
                 on_finish: Callable[[OutboundCall], None], ring_timeout: float = 45.0, max_seconds: float = 60.0,
                 invite_timeout: float = 32.0, display_name: str = "HydraHive") -> None:
        if not number.isdigit():
            raise ValueError("Nummer darf nur Ziffern enthalten")       # dialrules prüft vorher, hier nur Notbremse
        self.sock, self.target, self.local, self.rtp_sock = sock, target, local, rtp_sock
        self._user, self._password, self._domain, self.number = user, password, domain, number
        self._audio, self._on_finish, self._display = audio, on_finish, display_name.replace('"', "")
        self._ring_timeout, self._max, self._invite_timeout = ring_timeout, max_seconds, invite_timeout
        self.uri = f"sip:{number}@{domain}"
        self.call_id = os.urandom(12).hex() + "@hydrahive"
        self.from_tag = os.urandom(4).hex()
        self.cseq, self.branch, self.remote_tag, self.remote_uri = 0, "", "", self.uri
        self.state, self.result, self.codec = "calling", "", ""
        self.rtp_out = self.rtp_in = 0
        self._responses: queue.Queue[message.Message] = queue.Queue()
        self._ok_raw: bytes | None = None
        self._ack_raw: bytes | None = None
        self._hangup, self._ended, self._bye_ok = threading.Event(), threading.Event(), threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"tel-out-{self.call_id[:8]}", daemon=True)

    # ---- von außen ----
    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        if self._thread.is_alive():
            self._thread.join(timeout)

    def hangup(self) -> None:
        self._hangup.set()

    def on_response(self, msg: message.Message) -> None:
        if msg.header("call-id") != self.call_id:
            return
        if msg.status == 200 and (msg.header("cseq") or "").endswith(" INVITE") and self._ack_raw:
            self._send(self._ack_raw)                         # 200 wiederholt → ACK wiederholen (§13.2.2.4)
            return
        if (msg.header("cseq") or "").endswith(" BYE") and msg.status >= 200:
            self._bye_ok.set()
            return
        self._responses.put(msg)

    def on_request(self, msg: message.Message, addr: tuple[str, int]) -> None:
        if msg.method == "BYE":
            self._send(message.build_response(msg, 200, "OK"))
            self._end("remote_hangup")
        elif msg.method != "ACK":
            self._send(message.build_response(msg, 200 if msg.method == "OPTIONS" else 488, "OK"))

    # ---- SIP ----
    def _send(self, raw: bytes) -> None:
        try:
            self.sock.sendto(raw, self.target)
        except OSError:
            pass

    def _base(self, method: str, cseq: int, branch: str, to_tag: str = "") -> list[tuple[str, str]]:
        return [("Via", f"SIP/2.0/UDP {self.local[0]}:{self.local[1]};rport;branch={branch}"), ("Max-Forwards", "70"),
                ("From", f'"{self._display}" <sip:{self._user}@{self._domain}>;tag={self.from_tag}'),
                ("To", f"<{self.uri}>" + (f";tag={to_tag}" if to_tag else "")), ("Call-ID", self.call_id),
                ("CSeq", f"{cseq} {method}")]

    def _invite(self, auth: tuple[str, str] | None) -> bytes:
        self.cseq += 1
        self.branch = "z9hG4bK" + os.urandom(8).hex()
        body = sdp.offer(self.local[0], self.rtp_sock.getsockname()[1], session_id=int(time.time()))
        headers = [*self._base("INVITE", self.cseq, self.branch),
                   ("Contact", f"<sip:{self._user}@{self.local[0]}:{self.local[1]}>"),
                   ("Allow", "INVITE, ACK, CANCEL, BYE, OPTIONS"), ("User-Agent", "HydraHive"),
                   ("Content-Type", "application/sdp")]
        return message.build_request("INVITE", self.uri, headers + ([auth] if auth else []), body)

    def _ack_error(self, resp: message.Message) -> None:
        headers = self._base("ACK", self.cseq, self.branch)
        headers[3] = ("To", resp.header("to") or "")
        self._send(message.build_request("ACK", self.uri, headers))

    def _cancel(self) -> bytes:
        return message.build_request("CANCEL", self.uri, self._base("CANCEL", self.cseq, self.branch))

    def _end(self, result: str) -> None:
        if not self._ended.is_set():
            self.result = result
            self._ended.set()

    # ---- Ablauf ----
    def _run(self) -> None:
        try:
            ok = self._dial()
            if ok is not None:
                self._talk(ok)
        finally:
            self._ended.set()
            self.state = "ended"
            try:
                self.rtp_sock.close()
            except OSError:
                pass
            self._on_finish(self)

    def _dial(self) -> message.Message | None:
        from .outbound_flow import dial
        return dial(self)

    def _talk(self, ok: message.Message) -> None:
        from .outbound_flow import talk
        talk(self, ok)

    def _bye(self) -> None:
        raw = message.build_request("BYE", self.remote_uri, self._base("BYE", self.cseq + 1, "z9hG4bK" +
                                                                       os.urandom(8).hex(), self.remote_tag))
        wait = _T1
        for _ in range(4):
            self._send(raw)
            if self._bye_ok.wait(wait):
                return
            wait = min(wait * 2, _T2)

    def _listen(self, remote_ip: str) -> None:
        self.rtp_sock.settimeout(0.2)
        while not self._ended.is_set():
            try:
                data, addr = self.rtp_sock.recvfrom(2048)
            except TimeoutError:
                continue
            except OSError:
                return
            if addr[0] == remote_ip and rtp.parse(data) is not None:
                self.rtp_in += 1

    def _stream(self, offer: sdp.Offer, pt: int) -> None:
        audio = self._audio(self.codec)[: int(self._max * 8000)]
        self.rtp_out = rtp.send_stream(self.rtp_sock, (offer.address, offer.port), audio, payload_type=pt,
                                       stop=lambda: self._ended.is_set() or self._hangup.is_set(),
                                       silence=g711.SILENCE[self.codec])

    def digest_header(self, resp: message.Message) -> tuple[str, str]:
        proxy = resp.status == 407
        hdr = resp.header("proxy-authenticate" if proxy else "www-authenticate") or ""
        value = digest.authorization(digest.parse_challenge(hdr), "INVITE", self.uri, self._user, self._password)
        return ("Proxy-Authorization" if proxy else "Authorization", value)

    def final_result(self, status: int) -> str:
        return _FINAL.get(status, "failed")
