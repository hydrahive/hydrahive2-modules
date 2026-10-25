"""SDP (RFC 4566/3264) lesen/beantworten und RTP (RFC 3550) senden/empfangen."""
from __future__ import annotations

import socket
import struct
import time

import pytest

OFFER = (b"v=0\r\no=user 1 1 IN IP4 192.168.3.1\r\ns=call\r\nc=IN IP4 192.168.3.1\r\nt=0 0\r\n"
         b"m=audio 7082 RTP/AVP 9 8 0 101\r\na=rtpmap:9 G722/8000\r\na=rtpmap:8 PCMA/8000\r\n"
         b"a=rtpmap:0 PCMU/8000\r\na=rtpmap:101 telephone-event/8000\r\na=fmtp:101 0-15\r\na=sendrecv\r\n"
         b"a=ptime:20\r\n")


def test_angebot_lesen() -> None:
    from backend.sip import sdp

    o = sdp.parse_offer(OFFER)
    assert o.address == "192.168.3.1" and o.port == 7082
    assert o.payloads == [9, 8, 0, 101]
    assert o.codec_for(8) == "PCMA" and o.codec_for(0) == "PCMU"


def test_waehlt_ersten_unterstuetzten_codec_in_reihenfolge_der_anlage() -> None:
    from backend.sip import sdp

    assert sdp.choose(sdp.parse_offer(OFFER)) == (8, "PCMA")
    pcmu_first = OFFER.replace(b"RTP/AVP 9 8 0 101", b"RTP/AVP 0 8")
    assert sdp.choose(sdp.parse_offer(pcmu_first)) == (0, "PCMU")


def test_statische_payloads_ohne_rtpmap() -> None:
    from backend.sip import sdp

    o = sdp.parse_offer(b"v=0\r\nc=IN IP4 10.0.0.5\r\nm=audio 4000 RTP/AVP 0\r\n")
    assert sdp.choose(o) == (0, "PCMU") and o.address == "10.0.0.5"


def test_medienadresse_im_m_block_hat_vorrang() -> None:
    from backend.sip import sdp

    o = sdp.parse_offer(b"v=0\r\nc=IN IP4 10.0.0.1\r\nm=audio 4000 RTP/AVP 8\r\nc=IN IP4 10.0.0.9\r\n")
    assert o.address == "10.0.0.9"


@pytest.mark.parametrize("body", [
    b"", b"v=0\r\n", b"v=0\r\nc=IN IP4 10.0.0.1\r\nm=video 4000 RTP/AVP 96\r\n",
    b"v=0\r\nc=IN IP6 ::1\r\nm=audio 4000 RTP/AVP 8\r\n", b"v=0\r\nc=IN IP4 10.0.0.1\r\nm=audio 0 RTP/AVP 8\r\n",
    b"v=0\r\nc=IN IP4 10.0.0.1\r\nm=audio 4000 RTP/SAVP 8\r\n", b"v=0\r\nc=IN IP4 10.0.0.1\r\nm=audio x RTP/AVP 8\r\n",
])
def test_unbrauchbare_angebote(body: bytes) -> None:
    from backend.sip import sdp

    with pytest.raises(sdp.SdpError):
        sdp.parse_offer(body)


def test_kein_gemeinsamer_codec() -> None:
    from backend.sip import sdp

    with pytest.raises(sdp.SdpError):
        sdp.choose(sdp.parse_offer(OFFER.replace(b"RTP/AVP 9 8 0 101", b"RTP/AVP 9 101")))


def test_antwort_bauen() -> None:
    from backend.sip import sdp

    body = sdp.answer("192.168.3.29", 7078, 8, "PCMA", session_id=42).decode()
    assert body.startswith("v=0\r\n")
    for line in ("o=HydraHive 42 42 IN IP4 192.168.3.29", "c=IN IP4 192.168.3.29", "m=audio 7078 RTP/AVP 8",
                 "a=rtpmap:8 PCMA/8000", "a=ptime:20", "a=sendrecv"):
        assert line + "\r\n" in body
    assert sdp.parse_offer(body.encode()).port == 7078


# ---- RTP ----

def test_rtp_paket_bauen_und_lesen() -> None:
    from backend.media import rtp

    raw = rtp.packet(payload_type=8, seq=65535, timestamp=160, ssrc=0x11223344, payload=b"\xd5" * 160, marker=True)
    assert len(raw) == 12 + 160
    b0, b1, seq, ts, ssrc = struct.unpack("!BBHII", raw[:12])
    assert b0 == 0x80 and b1 == 0x80 | 8 and seq == 65535 and ts == 160 and ssrc == 0x11223344
    h = rtp.parse(raw)
    assert (h.payload_type, h.seq, h.timestamp, h.ssrc, len(h.payload)) == (8, 65535, 160, 0x11223344, 160)


@pytest.mark.parametrize("raw", [b"", b"\x80" * 11, b"\x40" + b"\x00" * 20])
def test_kaputte_rtp_pakete(raw: bytes) -> None:
    from backend.media import rtp

    assert rtp.parse(raw) is None


def test_sender_takt_sequenz_und_zeitstempel() -> None:
    from backend.media import rtp

    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tx.bind(("127.0.0.1", 0))
    rx.settimeout(1)
    try:
        audio = bytes(range(256)) * 5                      # 1280 Byte = 8 Pakete à 160
        t0 = time.monotonic()
        sent = rtp.send_stream(tx, ("127.0.0.1", rx.getsockname()[1]), audio, payload_type=8,
                               stop=lambda: False, silence=0xD5)
        took = time.monotonic() - t0
        got = [rtp.parse(rx.recvfrom(2048)[0]) for _ in range(8)]
    finally:
        rx.close()
        tx.close()
    assert sent == 8
    assert 0.12 <= took <= 0.4, "8 × 20 ms im Takt, nicht alles auf einmal"
    assert [p.seq - got[0].seq for p in got] == list(range(8))
    assert [p.timestamp - got[0].timestamp for p in got] == [i * 160 for i in range(8)]
    assert len({p.ssrc for p in got}) == 1 and got[0].marker and not got[1].marker
    assert b"".join(p.payload for p in got) == audio


def test_sender_fuellt_letztes_paket_mit_stille_und_stoppt_sofort() -> None:
    from backend.media import rtp

    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.settimeout(1)
    try:
        assert rtp.send_stream(tx, ("127.0.0.1", rx.getsockname()[1]), b"\x01" * 100, payload_type=0,
                               stop=lambda: False, silence=0xFF) == 1
        p = rtp.parse(rx.recvfrom(2048)[0])
        assert p.payload == b"\x01" * 100 + b"\xff" * 60
        n = rtp.send_stream(tx, ("127.0.0.1", rx.getsockname()[1]), b"\x01" * 16000, payload_type=0,
                            stop=lambda: True, silence=0xFF)
        assert n == 0
    finally:
        rx.close()
        tx.close()
