"""G.711 A-law (PCMA) und µ-law (PCMU) nach ITU-T G.711 – wie CPython audioop (lin2alaw/lin2ulaw).

audioop gibt es ab Python 3.13 nicht mehr. Die Kodierung wird einmal als Tabelle über alle 65536 Werte vorberechnet.
Dazu: Umrechnen auf 8 kHz Mono (Telefonqualität) mit einfachem Tiefpass (Mittelwert je Ausgabewert).
"""
from __future__ import annotations

import struct
from functools import lru_cache

SILENCE = {"PCMA": 0xD5, "PCMU": 0xFF}
_SEG_A = (0x1F, 0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF)
_SEG_U = (0x3F, 0x7F, 0xFF, 0x1FF, 0x3FF, 0x7FF, 0xFFF, 0x1FFF)


def _seg(value: int, table: tuple[int, ...]) -> int:
    for i, end in enumerate(table):
        if value <= end:
            return i
    return len(table)


def _alaw(sample: int) -> int:
    v = sample >> 3                                     # 13 Bit
    if v >= 0:
        mask = 0xD5
    else:
        mask, v = 0x55, -v - 1
    seg = _seg(v, _SEG_A)
    if seg >= 8:
        return 0x7F ^ mask
    quant = (v >> 1) if seg < 2 else (v >> seg)
    return ((seg << 4) | (quant & 0x0F)) ^ mask


def _ulaw(sample: int) -> int:
    v = sample >> 2                                     # 14 Bit
    if v < 0:
        v, mask = -v, 0x7F
    else:
        mask = 0xFF
    v = min(v, 8159) + 0x21
    seg = _seg(v, _SEG_U)
    if seg >= 8:
        return 0x7F ^ mask
    return ((seg << 4) | ((v >> (seg + 1)) & 0x0F)) ^ mask


@lru_cache(maxsize=2)
def _table(codec: str) -> bytes:
    fn = {"PCMA": _alaw, "PCMU": _ulaw}[codec]
    return bytes(fn(s - 65536 if s >= 32768 else s) for s in range(65536))


def encode(pcm16: bytes, codec: str) -> bytes:
    """PCM 16 Bit little-endian → G.711-Bytes (ein Byte je Wert)."""
    if codec not in SILENCE:
        raise ValueError(f"Codec {codec} nicht unterstützt")
    if len(pcm16) % 2:
        raise ValueError("PCM-Länge muss gerade sein")
    table = _table(codec)
    return bytes(table[s & 0xFFFF] for s in memoryview(pcm16).cast("h"))


def to_8k_mono(pcm16: bytes, *, rate: int, channels: int) -> bytes:
    """PCM 16 Bit (beliebige Rate, 1–2 Kanäle) → 8 kHz Mono."""
    samples = memoryview(pcm16[: len(pcm16) - len(pcm16) % (2 * channels)]).cast("h")
    mono = list(samples) if channels == 1 else [
        int(sum(samples[i:i + channels]) / channels) for i in range(0, len(samples), channels)]
    if rate == 8000:
        return struct.pack(f"<{len(mono)}h", *mono)
    step = rate / 8000
    count = int(len(mono) / step)
    out = []
    for n in range(count):
        lo, hi = int(n * step), max(int((n + 1) * step), int(n * step) + 1)
        window = mono[lo:hi]
        out.append(round(sum(window) / len(window)))
    return struct.pack(f"<{len(out)}h", *out)
