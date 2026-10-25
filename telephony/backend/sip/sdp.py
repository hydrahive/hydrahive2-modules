"""SDP-Angebot der Anlage lesen und beantworten (RFC 4566, RFC 3264) – nur Audio, nur G.711.

Gewählt wird der erste vom Angebot genannte Codec, den HydraHive kann (Reihenfolge der Anlage zählt).
Verschlüsseltes RTP (SAVP), IPv6 und Port 0 (abgelehnter Strom) werden nicht angenommen.
"""
from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field

_STATIC = {0: "PCMU", 8: "PCMA"}
SUPPORTED = ("PCMA", "PCMU")


class SdpError(ValueError):
    pass


@dataclass
class Offer:
    address: str
    port: int
    payloads: list[int]
    rtpmap: dict[int, str] = field(default_factory=dict)

    def codec_for(self, pt: int) -> str | None:
        name = self.rtpmap.get(pt)
        if name is None:
            return _STATIC.get(pt)
        return name if name in SUPPORTED else None


def parse_offer(body: bytes) -> Offer:
    try:
        lines = body.decode("utf-8").replace("\r\n", "\n").split("\n")
    except UnicodeDecodeError as e:
        raise SdpError("SDP kein UTF-8") from e
    session_addr = media_addr = None
    port, payloads, rtpmap, in_audio = None, [], {}, False
    for line in lines:
        if len(line) < 2 or line[1] != "=":
            continue
        kind, value = line[0], line[2:].strip()
        if kind == "m":
            parts = value.split()
            in_audio = bool(parts) and parts[0] == "audio" and port is None
            if in_audio:
                if len(parts) < 4 or parts[2] != "RTP/AVP" or not parts[1].isdigit():
                    raise SdpError("Audio-Strom nicht unterstützt")
                port = int(parts[1])
                payloads = [int(p) for p in parts[3:] if p.isdigit()]
        elif kind == "c":
            parts = value.split()
            if len(parts) != 3 or parts[:2] != ["IN", "IP4"]:
                raise SdpError("nur IPv4")
            if in_audio:
                media_addr = parts[2]
            elif port is None:
                session_addr = parts[2]
        elif kind == "a" and in_audio and value.startswith("rtpmap:"):
            pt, _, enc = value[7:].partition(" ")
            if pt.isdigit():
                rtpmap[int(pt)] = enc.split("/")[0].upper()
    address = media_addr or session_addr
    if port is None or not address:
        raise SdpError("kein Audio-Strom")
    if not 0 < port < 65536:
        raise SdpError("Port ungültig")
    try:
        ipaddress.IPv4Address(address)
    except ValueError as e:
        raise SdpError("Adresse ungültig") from e
    return Offer(address=address, port=port, payloads=payloads, rtpmap=rtpmap)


def choose(offer: Offer) -> tuple[int, str]:
    for pt in offer.payloads:
        codec = offer.codec_for(pt)
        if codec in SUPPORTED:
            return pt, codec
    raise SdpError("kein gemeinsamer Codec")


def answer(address: str, port: int, pt: int, codec: str, *, session_id: int) -> bytes:
    lines = ["v=0", f"o=HydraHive {session_id} {session_id} IN IP4 {address}", "s=HydraHive",
             f"c=IN IP4 {address}", "t=0 0", f"m=audio {port} RTP/AVP {pt}", f"a=rtpmap:{pt} {codec}/8000",
             "a=ptime:20", "a=sendrecv"]
    return ("\r\n".join(lines) + "\r\n").encode()


def offer(address: str, port: int, *, session_id: int) -> bytes:
    """Eigenes Angebot für ausgehende Anrufe: G.711 A-law zuerst, dann µ-law (PLAN-ANRUFEN-3)."""
    lines = ["v=0", f"o=HydraHive {session_id} {session_id} IN IP4 {address}", "s=HydraHive",
             f"c=IN IP4 {address}", "t=0 0", f"m=audio {port} RTP/AVP 8 0", "a=rtpmap:8 PCMA/8000",
             "a=rtpmap:0 PCMU/8000", "a=ptime:20", "a=sendrecv"]
    return ("\r\n".join(lines) + "\r\n").encode()
