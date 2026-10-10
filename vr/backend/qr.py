"""Minimaler QR-Encoder (Byte-Modus, Fehlerkorrektur M, Version 1–10) → SVG.

Bewusst ohne Fremdbibliothek: Der Kopplungs-QR enthält nur ~120 Byte ASCII.
Implementiert nach ISO/IEC 18004; gegen die Referenz-Bibliothek `qrcode`
getestet (tests/test_qr.py vergleicht die Modul-Matrix Bit für Bit).
"""
from __future__ import annotations

# Pro Version (1-basiert): (Daten-Codewörter gesamt, EC-Codewörter je Block, [Blockgrößen])  – Level M
_M = {
    1: (16, 10, [16]), 2: (28, 16, [28]), 3: (44, 26, [44]), 4: (64, 18, [32, 32]),
    5: (86, 24, [43, 43]), 6: (108, 16, [27, 27, 27, 27]), 7: (124, 18, [31, 31, 31, 31]),
    8: (154, 22, [38, 38, 39, 39]), 9: (182, 22, [36, 36, 36, 37, 37]),
    10: (216, 26, [43, 43, 43, 43, 44]),
}
_ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38],
          8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}

# GF(256) mit Polynom 0x11D
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _rs(data: list[int], n: int) -> list[int]:
    gen = [1]
    for i in range(n):
        gen = [a ^ _mul(b, _EXP[i]) for a, b in zip(gen + [0], [0] + gen)]
    res = list(data) + [0] * n
    for i in range(len(data)):
        f = res[i]
        if f:
            for j, g in enumerate(gen):
                res[i + j] ^= _mul(g, f)
    return res[len(data):]


def _version_for(n_bytes: int) -> int:
    for v, (cap, _, _) in _M.items():
        count_bits = 8 if v < 10 else 16
        if 4 + count_bits + 8 * n_bytes <= cap * 8:
            return v
    raise ValueError("Text zu lang für den QR-Code (max. Version 10)")


def _codewords(data: bytes, v: int) -> list[int]:
    cap, ec_n, blocks = _M[v]
    bits = "0100" + format(len(data), "08b" if v < 10 else "016b") + "".join(format(b, "08b") for b in data)
    bits += "0" * min(4, cap * 8 - len(bits))
    bits += "0" * (-len(bits) % 8)
    words = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    pad = (0xEC, 0x11)
    while len(words) < cap:
        words.append(pad[(len(words) - len(bits) // 8) % 2])
    split, i = [], 0
    for size in blocks:
        split.append(words[i:i + size])
        i += size
    ecs = [_rs(b, ec_n) for b in split]
    out = [b[k] for k in range(max(blocks)) for b in split if k < len(b)]
    return out + [e[k] for k in range(ec_n) for e in ecs]


def _format_bits(mask: int) -> int:
    data = (0b00 << 3) | mask  # Level M = 00
    rem = data << 10
    for i in range(14, 9, -1):
        if rem >> i & 1:
            rem ^= 0x537 << (i - 10)
    return ((data << 10) | rem) ^ 0x5412


def _version_bits(v: int) -> int:
    rem = v << 12
    for i in range(17, 11, -1):
        if rem >> i & 1:
            rem ^= 0x1F25 << (i - 12)
    return (v << 12) | rem


_MASKS = [
    lambda r, c: (r + c) % 2 == 0, lambda r, c: r % 2 == 0, lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0, lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0, lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]
