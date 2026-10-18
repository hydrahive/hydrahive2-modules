"""EDID für den virtuellen Hochkant-Monitor (EVDI): gültig, richtige Größe und Taktung."""
from __future__ import annotations

import struct

import pytest

from renderer import edid


def _dtd(e: bytes) -> dict:
    return {"clock_hz": struct.unpack_from("<H", e, 54)[0] * 10_000,
            "w": e[56] | ((e[58] >> 4) << 8), "hblank": e[57] | ((e[58] & 0xF) << 8),
            "h": e[59] | ((e[61] >> 4) << 8), "vblank": e[60] | ((e[61] & 0xF) << 8)}


def test_gueltige_edid_1080x1920():
    e = edid.build(1080, 1920)
    assert len(e) == 128 and e[:8] == b"\x00\xff\xff\xff\xff\xff\xff\x00"
    assert sum(e) % 256 == 0
    d = _dtd(e)
    assert (d["w"], d["h"]) == (1080, 1920)
    hz = d["clock_hz"] / ((d["w"] + d["hblank"]) * (d["h"] + d["vblank"]))
    assert 59.5 < hz < 60.5
    assert b"HydraVitrine" in e
    assert e[18:20] == b"\x01\x03"                       # EDID 1.3


def test_grenzen_passen_zum_takt():
    e = edid.build(1080, 1920)
    i = e.index(b"\x00\x00\x00\xfd\x00")
    vmin, vmax, hmin, hmax, clk10 = e[i + 5:i + 10]
    d = _dtd(e)
    hkhz = d["clock_hz"] / (d["w"] + d["hblank"]) / 1000
    assert vmin <= 60 <= vmax and hmin <= hkhz <= hmax and d["clock_hz"] <= clk10 * 10_000_000


@pytest.mark.parametrize(("w", "h"), [(0, 1920), (1080, 0), (5000, 1920), (1080, 5000)])
def test_unsinnige_groesse_abgelehnt(w, h):
    with pytest.raises(ValueError):
        edid.build(w, h)


def test_byte_gleich_zur_am_geraet_geprueften_edid():
    # Am 18.10.2026 auf .2 mit Xorg + Display getestet (DVI-I-2-1, 1080x1920 @ 60 Hz)
    geprueft = bytes.fromhex(
        "00ffffffffffff002336201901000000" "01240103801322780aee91a3544c9926" "0f505400000001010101010101010101"
        "010101010101f63838a0408028703020" "3a00c25901000018000000fc00487964" "726156697472696e650a000000fd0018"
        "4c1e800f000a20202020202000000000" "000000000000000000000000000000fc")
    assert edid.build(1080, 1920) == geprueft
