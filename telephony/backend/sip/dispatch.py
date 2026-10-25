"""Verteilt eingehende Anrufe (PLAN-ANRUFE-2A): annehmen, ablehnen, besetzt – höchstens ein Anruf gleichzeitig.

``policy()`` liefert den Ansagetext, wenn angenommen werden soll, sonst None (→ 480 wie in 0.6.x). Jeder Anruf wird
über ``record`` gemeldet – mit maskierter Rufnummer, nie mit Inhalt.
"""
from __future__ import annotations

import re
import socket
import threading
import time
from collections.abc import Callable

from ..media import greeting as _greeting_mod
from . import message, sdp
from .call import CallSession

_NUM_RE = re.compile(r"sip:\+?([0-9]+)@")


def mask_number(from_header: str) -> str:
    m = _NUM_RE.search(from_header or "")
    if not m or len(m.group(1)) < 3:
        return "unbekannt"
    return "•••" + m.group(1)[-3:]


class CallDispatcher:
    def __init__(self, *, policy: Callable[[], str | None], rtp_ports: tuple[int, int],
                 record: Callable[[dict], None], greeting: Callable[[str, str], bytes] | None = None,
                 ring_seconds: float = 1.0, ack_timeout: float = 32.0, max_seconds: float = 60.0) -> None:
        self.policy, self.rtp_ports, self._record = policy, rtp_ports, record
        self._greeting = greeting or _greeting_mod.render
        self._ring, self._ack, self._max = ring_seconds, ack_timeout, max_seconds
        self._lock = threading.Lock()
        self._calls: dict[str, CallSession] = {}

    def _note(self, invite: message.Message, result: str, **extra) -> None:
        self._record({"number": mask_number(invite.header("from") or ""), "result": result,
                      "started_at": time.time(), **extra})

    def _bind_rtp(self, local_ip: str) -> socket.socket | None:
        lo, hi = self.rtp_ports
        for port in range(lo + (lo % 2), hi, 2):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.bind((local_ip, port))
                return s
            except OSError:
                s.close()
        return None

    def _finish(self, call: CallSession) -> None:
        with self._lock:
            self._calls.pop(call.call_id, None)
        self._note(call.invite, call.result, codec=call.codec, rtp_out=call.rtp_out, rtp_in=call.rtp_in)

    def handle_request(self, sock: socket.socket, msg: message.Message, addr: tuple[str, int], local_ip: str) -> bool:
        cid = msg.header("call-id") or ""
        with self._lock:
            call = self._calls.get(cid)
            busy = any(c.alive for c in self._calls.values())
        if call:
            call.on_request(msg, addr)
            return True
        if msg.method in ("BYE", "CANCEL"):
            sock.sendto(message.build_response(msg, 481, "Call/Transaction Does Not Exist"), addr)
            return True
        if msg.method == "ACK":
            return True
        if msg.method != "INVITE":
            return False
        reply = lambda code, reason: sock.sendto(
            message.build_response(msg, code, reason, to_tag="hh" + cid[-6:].replace(";", "")), addr)
        if busy:
            reply(486, "Busy Here")
            self._note(msg, "busy")
            return True
        text = self.policy()
        if text is None:
            reply(480, "Temporarily Unavailable")
            self._note(msg, "rejected")
            return True
        try:
            offer = sdp.parse_offer(msg.body)
            pt, codec = sdp.choose(offer)
        except sdp.SdpError:
            reply(488, "Not Acceptable Here")
            self._note(msg, "codec")
            return True
        rtp_sock = self._bind_rtp(local_ip)
        if rtp_sock is None:
            reply(503, "Service Unavailable")
            self._note(msg, "no_port")
            return True
        sock.sendto(message.build_response(msg, 100, "Trying"), addr)
        call = CallSession(sock=sock, invite=msg, remote=addr, local_ip=local_ip, offer=offer, pt=pt, codec=codec,
                           rtp_sock=rtp_sock, audio=lambda: self._greeting(text, codec), ring_seconds=self._ring,
                           ack_timeout=self._ack, max_seconds=self._max, on_finish=self._finish)
        with self._lock:
            self._calls[cid] = call
        call.start()
        return True

    def handle_response(self, msg: message.Message) -> None:
        with self._lock:
            call = self._calls.get(msg.header("call-id") or "")
        if call:
            call.on_response(msg)

    def hangup_all(self, timeout: float = 3.0) -> None:
        with self._lock:
            calls = list(self._calls.values())
        for c in calls:
            c.hangup()
        end = time.monotonic() + timeout
        for c in calls:
            c._thread.join(max(0.0, end - time.monotonic()))
