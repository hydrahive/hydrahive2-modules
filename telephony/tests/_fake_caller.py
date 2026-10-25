"""Test-Anrufer: verhält sich wie die FRITZ!Box bei einem eingehenden Anruf (SIP über UDP + RTP-Empfang).

Schickt INVITE mit SDP an HydraHive, sammelt alle Antworten, bestätigt 200 mit ACK, zählt empfangene RTP-Pakete,
beantwortet BYE mit 200. Kann CANCEL und BYE selbst schicken.
"""
from __future__ import annotations

import socket
import threading
import time

from backend.media import rtp
from backend.sip import message


class FakeCaller:
    def __init__(self, *, codecs: str = "8 0 101", send_rtp: bool = True, auto_ack: bool = True) -> None:
        self.sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sip.bind(("127.0.0.1", 0))
        self.rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp.bind(("127.0.0.1", 0))
        self.addr = self.sip.getsockname()
        self.codecs, self.send_rtp, self.auto_ack = codecs, send_rtp, auto_ack
        self.responses: list[message.Message] = []
        self.requests: list[message.Message] = []
        self.rtp_packets: list[rtp.RtpHeader] = []
        self.target: tuple[str, int] | None = None
        self.call_id = "inv-" + str(id(self))
        self._stop = threading.Event()
        self._threads = [threading.Thread(target=self._sip_loop, daemon=True),
                         threading.Thread(target=self._rtp_loop, daemon=True)]
        for t in self._threads:
            t.start()

    def close(self) -> None:
        self._stop.set()
        self.sip.close()
        self.rtp.close()

    def sdp(self) -> bytes:
        return (f"v=0\r\no=fritz 1 1 IN IP4 127.0.0.1\r\ns=call\r\nc=IN IP4 127.0.0.1\r\nt=0 0\r\n"
                f"m=audio {self.rtp.getsockname()[1]} RTP/AVP {self.codecs}\r\na=rtpmap:8 PCMA/8000\r\n"
                f"a=rtpmap:0 PCMU/8000\r\na=rtpmap:101 telephone-event/8000\r\na=sendrecv\r\n").encode()

    def _headers(self, method: str, cseq: int, to_tag: str | None = None) -> list[tuple[str, str]]:
        to = "<sip:hydra-telefon@127.0.0.1>" + (f";tag={to_tag}" if to_tag else "")
        return [("Via", f"SIP/2.0/UDP {self.addr[0]}:{self.addr[1]};branch=z9hG4bK{method}{cseq}"),
                ("From", "<sip:0301234567@fritz.box>;tag=fritz1"), ("To", to), ("Call-ID", self.call_id),
                ("CSeq", f"{cseq} {method}"), ("Contact", f"<sip:fritz@{self.addr[0]}:{self.addr[1]}>"),
                ("Max-Forwards", "70")]

    def invite(self, target: tuple[str, int], *, body: bytes | None = None) -> None:
        self.target = target
        self.sip.sendto(message.build_request("INVITE", f"sip:hydra-telefon@{target[0]}:{target[1]}",
                                              [*self._headers("INVITE", 1), ("Content-Type", "application/sdp")],
                                              body if body is not None else self.sdp()), target)

    def cancel(self) -> None:
        self.sip.sendto(message.build_request("CANCEL", "sip:hydra-telefon@x", self._headers("CANCEL", 1)[:-2]
                                              + [("Max-Forwards", "70")]), self.target)

    def bye(self) -> None:
        tag = self.to_tag()
        self.sip.sendto(message.build_request("BYE", "sip:hydra-telefon@x", self._headers("BYE", 2, tag)),
                        self.target)

    def ack(self) -> None:
        self.sip.sendto(message.build_request("ACK", "sip:hydra-telefon@x", self._headers("ACK", 1, self.to_tag())),
                        self.target)

    def to_tag(self) -> str | None:
        for r in self.responses:
            to = r.header("to") or ""
            if ";tag=" in to:
                return to.split(";tag=")[1].split(";")[0]
        return None

    def statuses(self) -> list[int]:
        return [r.status for r in self.responses]

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
            if m.is_request:
                self.requests.append(m)
                if m.method == "BYE":
                    self.sip.sendto(message.build_response(m, 200, "OK"), addr)
            else:
                self.responses.append(m)
                if m.status == 200 and "INVITE" in (m.header("cseq") or "") and self.auto_ack:
                    self.ack()
                    if self.send_rtp:
                        threading.Thread(target=self._talk, args=(m,), daemon=True).start()

    def _talk(self, ok: message.Message) -> None:
        from backend.sip import sdp

        try:
            o = sdp.parse_offer(ok.body)
        except sdp.SdpError:
            return
        for i in range(10):
            try:
                self.rtp.sendto(rtp.packet(payload_type=8, seq=i, timestamp=i * 160, ssrc=7, payload=b"\xd5" * 160),
                                (o.address, o.port))
            except OSError:
                return
            time.sleep(0.02)

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
