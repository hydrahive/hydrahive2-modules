"""G.711 A-law/µ-law (ITU-T G.711) – selbst kodiert, weil audioop ab Python 3.13 fehlt."""
from __future__ import annotations

import struct

import pytest

# Referenzwerte aus CPython audioop (lin2alaw/lin2ulaw, Referenz-Implementierung von G.711), erzeugt mit
# Python 3.12; dazu SHA-256 der Kodierung aller 65536 Werte.
ALAW = [(0, 0xD5), (1, 0xD5), (-1, 0x55), (8, 0xD5), (-8, 0x55), (16, 0xD4), (-16, 0x55), (100, 0xD3), (255, 0xDA), (256, 0xC5), (1000, 0xFA), (-1000, 0x7A), (4095, 0x9A), (8159, 0x8A), (-8159, 0x0A), (32767, 0xAA), (-32768, 0x2A), (-32767, 0x2A)]
ULAW = [(0, 0xFF), (1, 0xFF), (-1, 0x7E), (8, 0xFE), (-8, 0x7E), (16, 0xFD), (-16, 0x7D), (100, 0xF2), (255, 0xE7), (256, 0xE7), (1000, 0xCE), (-1000, 0x4E), (4095, 0xAF), (8159, 0x9F), (-8159, 0x1F), (32767, 0x80), (-32768, 0x00), (-32767, 0x00)]
ALL_ALAW_SHA256 = "38488f6fd710f4686360edc4d38639f96c491595ef93f8eb8d62d5e07ca6ce7b"
ALL_ULAW_SHA256 = "81d633c9e6972a18c74a58720b96cb8ca0bdd096d4060b646dd708c3b846019a"


@pytest.mark.parametrize("sample,code", ALAW)
def test_alaw(sample: int, code: int) -> None:
    from backend.media import g711

    assert g711.encode(struct.pack("<h", sample), "PCMA") == bytes([code])


@pytest.mark.parametrize("sample,code", ULAW)
def test_ulaw(sample: int, code: int) -> None:
    from backend.media import g711

    assert g711.encode(struct.pack("<h", sample), "PCMU") == bytes([code])


def test_alle_65536_werte_wie_referenz() -> None:
    import hashlib

    from backend.media import g711

    allpcm = struct.pack("<65536h", *range(-32768, 32768))
    assert hashlib.sha256(g711.encode(allpcm, "PCMA")).hexdigest() == ALL_ALAW_SHA256
    assert hashlib.sha256(g711.encode(allpcm, "PCMU")).hexdigest() == ALL_ULAW_SHA256


def test_ganzer_puffer_und_laenge() -> None:
    from backend.media import g711

    pcm = struct.pack("<4h", 0, 1000, -1000, 32767)
    assert g711.encode(pcm, "PCMA") == bytes([0xD5, 0xFA, 0x7A, 0xAA])
    assert len(g711.encode(b"\x00\x00" * 160, "PCMU")) == 160


def test_ungerade_laenge_und_unbekannter_codec() -> None:
    from backend.media import g711

    with pytest.raises(ValueError):
        g711.encode(b"\x00\x00\x00", "PCMA")
    with pytest.raises(ValueError):
        g711.encode(b"\x00\x00", "G722")


def test_stille_byte() -> None:
    from backend.media import g711

    assert g711.SILENCE == {"PCMA": 0xD5, "PCMU": 0xFF}


def test_resample_auf_8khz_und_mono() -> None:
    from backend.media import g711

    # 22050 Hz, 1 s, Mono → 8000 Samples
    pcm = struct.pack(f"<{22050}h", *([1000] * 22050))
    out = g711.to_8k_mono(pcm, rate=22050, channels=1)
    assert len(out) == 8000 * 2
    assert set(struct.unpack(f"<{8000}h", out)) == {1000}
    # Stereo → Mittelwert der Kanäle
    st = struct.pack("<4h", 100, 300, -100, -300)
    assert struct.unpack("<2h", g711.to_8k_mono(st, rate=8000, channels=2)) == (200, -200)
    # 16 kHz → 8 kHz: je zwei Werte gemittelt (einfacher Tiefpass gegen Aliasing)
    assert struct.unpack("<2h", g711.to_8k_mono(struct.pack("<4h", 100, 300, -50, -150), rate=16000,
                                                  channels=1)) == (200, -100)
    # 8 kHz Mono bleibt unverändert
    assert g711.to_8k_mono(b"\x01\x00\x02\x00", rate=8000, channels=1) == b"\x01\x00\x02\x00"


# ---- Dekodieren (Zuhören, Etappe 2b) – Referenz CPython audioop.alaw2lin/ulaw2lin ----
ALAW_DECODE_SHA256 = "e04788d110e58ff8c70c93b8480190d973e3b67876b6119abbaec766cc75c174"
ULAW_DECODE_SHA256 = "3dab54339e520bb2c924826e3b72a917a2b612e9fd12fc867500f1d983a75827"


def test_dekodieren_alle_256_werte_wie_referenz() -> None:
    import hashlib

    from backend.media import g711

    assert hashlib.sha256(g711.decode(bytes(range(256)), "PCMA")).hexdigest() == ALAW_DECODE_SHA256
    assert hashlib.sha256(g711.decode(bytes(range(256)), "PCMU")).hexdigest() == ULAW_DECODE_SHA256


def test_dekodieren_einzelwerte() -> None:
    from backend.media import g711

    assert struct.unpack("<4h", g711.decode(bytes([0xD5, 0x55, 0x2A, 0xAA]), "PCMA")) == (8, -8, -32256, 32256)
    assert struct.unpack("<4h", g711.decode(bytes([0xFF, 0x7F, 0x00, 0x80]), "PCMU")) == (0, 0, -32124, 32124)
    with pytest.raises(ValueError):
        g711.decode(b"\x00", "G722")


def test_hin_und_zurueck_bleibt_nah() -> None:
    from backend.media import g711

    for v in (0, 100, -100, 1000, -5000, 20000):
        back = struct.unpack("<h", g711.decode(g711.encode(struct.pack("<h", v), "PCMA"), "PCMA"))[0]
        assert abs(back - v) <= max(16, abs(v) // 16)


def test_8k_auf_16k() -> None:
    from backend.media import g711

    out = struct.unpack("<6h", g711.up_16k(struct.pack("<3h", 0, 100, -100)))
    assert out == (0, 50, 100, 0, -100, -100), "Zwischenwert gemittelt, letzter Wert doppelt"
    assert g711.up_16k(b"") == b""
