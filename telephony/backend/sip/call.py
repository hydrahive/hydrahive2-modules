"""Ein angenommener Anruf: klingeln, abnehmen, Ansage abspielen, auflegen (PLAN-ANRUFE-2A).

Läuft in einem eigenen Thread. Der SipAgent gibt Anfragen dieses Anrufs (ACK, BYE, CANCEL, Wiederholungen) über den
CallDispatcher hierher. Ton vom Anrufer wird nur gezählt (nur von der Adresse aus dem SDP), nie gespeichert.
"""
from __future__ import annotations

import os
import queue
import socket
import threading
import time
from collections.abc import Callable

from ..media import g711, rtp
from . import message, sdp

_T1, _T2 = 0.5, 4.0


class CallSession:
    def __init__(self, *, sock: socket.socket, invite: message.Message, remote: tuple[str, int], local_ip: str,
                 offer: sdp.Offer, pt: int, codec: str, rtp_sock: socket.socket, audio: Callable[[], bytes],
                 ring_seconds: float, ack_timeout: float, max_seconds: float,
                 on_finish: Callable[[CallSession], None], assistant: dict | None = None) -> None:
        self.sock, self.invite, self.remote, self.local_ip = sock, invite, remote, local_ip
        self.offer, self.pt, self.codec, self.rtp_sock = offer, pt, codec, rtp_sock
        self._audio, self._ring, self._ack_timeout, self._max = audio, ring_seconds, ack_timeout, max_seconds
        self._on_finish = on_finish
        self._assistant = assistant                             # None = nur Ansage (2a); sonst Telefon-Assistent (2b)
        self._voice: queue.Queue[bytes | None] = queue.Queue(maxsize=500)
        self.turns, self.notes = 0, {}
        self.call_id = invite.header("call-id") or ""
        self.to_tag = os.urandom(4).hex()
        self.state = "ringing"
        self.result = "answered"
        self.rtp_out = self.rtp_in = 0
        self._acked, self._ended, self._bye_ok = threading.Event(), threading.Event(), threading.Event()
        self._last: bytes | None = None
        self._thread = threading.Thread(target=self._run, name=f"tel-call-{self.call_id[:8]}", daemon=True)

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        self._thread.start()

    # ---- SIP ----
    def _send(self, raw: bytes, *, remember: bool = True) -> None:
        if remember:
            self._last = raw
        try:
            self.sock.sendto(raw, self.remote)
        except OSError:
            pass

    def respond(self, status: int, reason: str, body: bytes = b"") -> None:
        extra = [("Contact", f"<sip:hydrahive@{self.local_ip}:{self.sock.getsockname()[1]}>")]
        if body:
            extra.append(("Content-Type", "application/sdp"))
        self._send(message.build_response(self.invite, status, reason, to_tag=self.to_tag, extra=extra, body=body))

    def on_request(self, msg: message.Message, addr: tuple[str, int]) -> None:
        m = msg.method
        if m == "INVITE":
            if ";tag=" in (msg.header("to") or ""):           # re-INVITE im Gespräch: in 2a nicht unterstützt
                self._send(message.build_response(msg, 488, "Not Acceptable Here"), remember=False)
            elif self._last:
                self._send(self._last)                        # Wiederholung des INVITE: letzte Antwort erneut
        elif m == "ACK":
            self._acked.set()
        elif m == "CANCEL":
            self._send(message.build_response(msg, 200, "OK"), remember=False)
            if self.state == "ringing":
                self.respond(487, "Request Terminated")
                self._end("cancelled")
        elif m == "BYE":
            self._send(message.build_response(msg, 200, "OK"), remember=False)
            self._end("caller_hangup")
        else:
            self._send(message.build_response(msg, 200 if m == "OPTIONS" else 405, "OK"), remember=False)

    def on_response(self, msg: message.Message) -> None:
        if (msg.header("cseq") or "").endswith(" BYE") and msg.status >= 200:
            self._bye_ok.set()

    def _end(self, result: str) -> None:
        if not self._ended.is_set():
            self.result = result
            self._ended.set()

    def hangup(self) -> None:
        if self.state == "answered":
            self._end("hung_up")

    def _bye(self) -> None:
        contact = (self.invite.header("contact") or "").strip().lstrip("<").split(">")[0] or f"sip:{self.remote[0]}"
        port = self.sock.getsockname()[1]
        raw = message.build_request("BYE", contact, [
            ("Via", f"SIP/2.0/UDP {self.local_ip}:{port};rport;branch=z9hG4bK{os.urandom(8).hex()}"),
            ("Max-Forwards", "70"), ("From", f"{self.invite.header('to')};tag={self.to_tag}"),
            ("To", self.invite.header("from") or ""), ("Call-ID", self.call_id), ("CSeq", "1 BYE")])
        wait = _T1
        for _ in range(4):
            self._send(raw, remember=False)
            if self._bye_ok.wait(wait):
                return
            wait = min(wait * 2, _T2)

    # ---- Ablauf ----
    def _run(self) -> None:
        try:
            self.respond(180, "Ringing")
            ring_end = time.monotonic() + self._ring
            audio = self._audio()                               # Ansage vorbereiten, während es klingelt
            if self._ended.wait(max(0.0, ring_end - time.monotonic())):
                return
            self.state = "answered"
            self.respond(200, "OK", sdp.answer(self.local_ip, self.rtp_sock.getsockname()[1], self.pt, self.codec,
                                               session_id=int(time.time())))
            if not self._wait_ack():
                self._end("no_ack")
                self._bye()
                return
            threading.Thread(target=self._listen, daemon=True).start()
            if self._assistant is not None:
                self._converse()
                return
            audio = audio[: int(self._max * 8000)]
            self.rtp_out = rtp.send_stream(self.rtp_sock, (self.offer.address, self.offer.port), audio,
                                           payload_type=self.pt, stop=self._ended.is_set,
                                           silence=g711.SILENCE[self.codec])
            if not self._ended.wait(0.5):
                self._end("answered")
                self._bye()
        finally:
            self._ended.set()
            try:
                self.rtp_sock.close()
            except OSError:
                pass
            self._on_finish(self)

    def _wait_ack(self) -> bool:
        end, wait = time.monotonic() + self._ack_timeout, _T1
        while time.monotonic() < end:
            if self._acked.wait(min(wait, max(0.0, end - time.monotonic()))) or self._ended.is_set():
                return self._acked.is_set()
            if self._last:
                self._send(self._last)                          # 200 OK wiederholen (RFC 3261 §13.3.1.4)
            wait = min(wait * 2, _T2)
        return self._acked.is_set()

    def _listen(self) -> None:
        self.rtp_sock.settimeout(0.2)
        while not self._ended.is_set():
            try:
                data, addr = self.rtp_sock.recvfrom(2048)
            except TimeoutError:
                continue
            except OSError:
                return
            pkt = rtp.parse(data) if addr[0] == self.offer.address else None
            if pkt is None:
                continue
            self.rtp_in += 1
            if self._assistant is not None and len(pkt.payload) == 160:
                try:
                    self._voice.put_nowait(g711.decode(pkt.payload, self.codec))   # nur im Speicher, nie abgelegt
                except (queue.Full, ValueError):
                    pass

    # ---- Telefon-Assistent (Etappe 2b) ----
    def _say_rtp(self, text: str, interrupted: Callable[[], bool]) -> bool:
        audio = self._assistant["tts"](text, self.codec)[: int(self._max * 8000)]
        sent = rtp.send_stream(self.rtp_sock, (self.offer.address, self.offer.port), audio, payload_type=self.pt,
                               stop=lambda: interrupted() or self._ended.is_set(), silence=g711.SILENCE[self.codec])
        self.rtp_out += sent
        return sent * 160 >= len(audio)

    def _converse(self) -> None:
        from ..agent.conversation import Conversation

        a = self._assistant
        conv = Conversation(cfg=a["cfg"], llm=a["llm"], stt=a["stt"], say=self._say_rtp, frames=self._voice,
                            hangup=self._ended.is_set, max_seconds=self._max, **a.get("options", {}))
        result = conv.run()
        self.turns, self.notes = result.turns, result.notes
        if not self._ended.is_set():
            self._end(result.reason)
            self._bye()

