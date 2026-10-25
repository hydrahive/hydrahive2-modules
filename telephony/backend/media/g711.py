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


def _alaw_dec(code: int) -> int:
    code ^= 0x55
    seg, mant = (code >> 4) & 0x07, code & 0x0F
    v = (mant << 4) + 8 if seg == 0 else ((mant << 4) + 0x108) << (seg - 1)
    return v if code & 0x80 else -v


def _ulaw_dec(code: int) -> int:
    code = ~code & 0xFF
    seg, mant = (code >> 4) & 0x07, code & 0x0F
    v = (((mant << 3) + 0x84) << seg) - 0x84
    return -v if code & 0x80 else v


@lru_cache(maxsize=2)
def _dec_table(codec: str) -> tuple[int, ...]:
    fn = {"PCMA": _alaw_dec, "PCMU": _ulaw_dec}[codec]
    return tuple(fn(c) for c in range(256))


def decode(data: bytes, codec: str) -> bytes:
    """G.711-Bytes → PCM 16 Bit little-endian (wie CPython audioop.alaw2lin/ulaw2lin)."""
    if codec not in SILENCE:
        raise ValueError(f"Codec {codec} nicht unterstützt")
    table = _dec_table(codec)
    return struct.pack(f"<{len(data)}h", *(table[b] for b in data))


def up_16k(pcm8k: bytes) -> bytes:
    """8 kHz → 16 kHz (für Whisper): je Wert ein gemittelter Zwischenwert."""
    s = memoryview(pcm8k[: len(pcm8k) - len(pcm8k) % 2]).cast("h")
    out: list[int] = []
    for i, v in enumerate(s):
        nxt = s[i + 1] if i + 1 < len(s) else v
        out += (v, (v + nxt) // 2)
    return struct.pack(f"<{len(out)}h", *out)
