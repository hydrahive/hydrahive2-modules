"""RTP-Pakete (RFC 3550) bauen/lesen und G.711-Ton im 20-ms-Takt senden.

Ein Paket = 20 ms = 160 Werte bei 8 kHz. Zeitstempel +160 je Paket, Sequenz +1, zufälliger SSRC und Startwerte,
Marker-Bit am ersten Paket. Gesendet wird nach Uhr (Sollzeit je Paket), nicht „so schnell wie möglich“.
"""
from __future__ import annotations

import os
import socket
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass

FRAME = 160
FRAME_SECONDS = 0.02
_HDR = struct.Struct("!BBHII")


@dataclass
class RtpHeader:
    payload_type: int
    seq: int
    timestamp: int
    ssrc: int
    marker: bool
    payload: bytes


def packet(*, payload_type: int, seq: int, timestamp: int, ssrc: int, payload: bytes, marker: bool = False) -> bytes:
    return _HDR.pack(0x80, (0x80 if marker else 0) | (payload_type & 0x7F), seq & 0xFFFF,
                     timestamp & 0xFFFFFFFF, ssrc & 0xFFFFFFFF) + payload


def parse(raw: bytes) -> RtpHeader | None:
    if len(raw) < 12 or raw[0] >> 6 != 2:
        return None
    b0, b1, seq, ts, ssrc = _HDR.unpack_from(raw)
    start = 12 + 4 * (b0 & 0x0F)
    if start > len(raw):
        return None
    return RtpHeader(payload_type=b1 & 0x7F, seq=seq, timestamp=ts, ssrc=ssrc, marker=bool(b1 & 0x80),
                     payload=raw[start:])


def send_stream(sock: socket.socket, dest: tuple[str, int], audio: bytes, *, payload_type: int,
                stop: Callable[[], bool], silence: int) -> int:
    """G.711-Bytes als RTP senden. Gibt die Zahl gesendeter Pakete zurück; ``stop()`` bricht sofort ab."""
    seq = int.from_bytes(os.urandom(2), "big")
    ts = int.from_bytes(os.urandom(4), "big")
    ssrc = int.from_bytes(os.urandom(4), "big")
    start, sent = time.monotonic(), 0
    for offset in range(0, len(audio), FRAME):
        if stop():
            break
        due = start + sent * FRAME_SECONDS
        wait = due - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        chunk = audio[offset:offset + FRAME]
        if len(chunk) < FRAME:
            chunk += bytes([silence]) * (FRAME - len(chunk))
        try:
            sock.sendto(packet(payload_type=payload_type, seq=seq + sent, timestamp=ts + sent * FRAME, ssrc=ssrc,
                               payload=chunk, marker=sent == 0), dest)
        except OSError:
            break
        sent += 1
    return sent
