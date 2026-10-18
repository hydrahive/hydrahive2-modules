"""EDID (128 Byte, Version 1.3) für den virtuellen Monitor (EVDI), Standard 1080×1920 bei 60 Hz.

Der Aufbau folgt der VESA-Norm. Als Vorbild diente tinyscreen/edid.py (MIT, siehe UPSTREAM.md); Größe, Taktung und Grenzen
werden hier berechnet statt fest eingetragen. Am 18.10.2026 auf .2 mit `edid-decode` und Xorg geprüft.
"""
from __future__ import annotations

import struct

NAME = b"HydraVitrine"
H_FRONT, H_SYNC, H_BLANK = 48, 32, 160
V_FRONT, V_SYNC, V_BLANK = 3, 10, 40


def _dtd(e: bytearray, w: int, h: int, clock: int) -> None:
    struct.pack_into("<H", e, 54, round(clock / 10_000))
    e[56], e[57], e[58] = w & 0xFF, H_BLANK & 0xFF, ((w >> 8) & 0xF) << 4 | ((H_BLANK >> 8) & 0xF)
    e[59], e[60], e[61] = h & 0xFF, V_BLANK & 0xFF, ((h >> 8) & 0xF) << 4 | ((V_BLANK >> 8) & 0xF)
    e[62], e[63], e[64], e[65] = H_FRONT, H_SYNC, ((V_FRONT & 0xF) << 4) | (V_SYNC & 0xF), 0
    wmm, hmm = 194, 345                                           # 15,6" hochkant
    e[66], e[67], e[68] = wmm & 0xFF, hmm & 0xFF, ((wmm >> 8) & 0xF) << 4 | ((hmm >> 8) & 0xF)
    e[71] = 0x18                                                  # nicht interlaced, digital, getrennte Sync


def build(w: int = 1080, h: int = 1920, hz: int = 60) -> bytes:
    if not (320 <= w <= 4095 and 200 <= h <= 4095 and 24 <= hz <= 75):
        raise ValueError(f"EDID: unpassende Größe {w}x{h}@{hz}")
    e = bytearray(128)
    e[0:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"
    struct.pack_into(">H", e, 8, (8 << 10) | (25 << 5) | 22)     # Hersteller „HYV“
    struct.pack_into("<H", e, 10, 0x1920)
    struct.pack_into("<I", e, 12, 1)
    e[16], e[17], e[18], e[19], e[20] = 1, 2026 - 1990, 1, 3, 0x80
    e[21], e[22], e[23], e[24] = 19, 34, 120, 0x0A
    e[25:35] = bytes([0xEE, 0x91, 0xA3, 0x54, 0x4C, 0x99, 0x26, 0x0F, 0x50, 0x54])
    for i in range(38, 54, 2):
        e[i], e[i + 1] = 1, 1
    clock = (w + H_BLANK) * (h + V_BLANK) * hz
    _dtd(e, w, h, clock)
    e[72:77] = b"\x00\x00\x00\xfc\x00"
    e[77:90] = (NAME[:12] + b"\n").ljust(13, b" ")
    hkhz = (h + V_BLANK) * hz // 1000 + 1                         # Zeilen/s in kHz, aufgerundet (wie am Gerät geprüft)
    e[90:95] = b"\x00\x00\x00\xfd\x00"
    e[95:100] = bytes([24, 76, 30, min(255, hkhz + 10), min(255, clock // 10_000_000 + 1)])
    e[101:108] = b"\x0a" + b" " * 6
    e[127] = (256 - sum(e[:127]) % 256) % 256
    return bytes(e)
