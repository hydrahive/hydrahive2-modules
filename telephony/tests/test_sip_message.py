"""SIP-Nachrichten bauen/lesen und Digest-Anmeldung (RFC 3261, RFC 2617/8760)."""
from __future__ import annotations

import pytest

_REG_401 = (
    b"SIP/2.0 401 Unauthorized\r\n"
    b"Via: SIP/2.0/UDP 192.168.178.20:5070;branch=z9hG4bKabc;rport=5070;received=192.168.178.20\r\n"
    b"From: <sip:hydra-telefon@fritz.box>;tag=111\r\n"
    b"To: <sip:hydra-telefon@fritz.box>;tag=srv\r\n"
    b"Call-ID: cid-1@hydrahive\r\n"
    b"CSeq: 1 REGISTER\r\n"
    b'WWW-Authenticate: Digest realm="fritz.box", nonce="ABCDEF0123", algorithm=MD5\r\n'
    b"Content-Length: 0\r\n\r\n"
)


def test_antwort_lesen() -> None:
    from backend.sip import message

    m = message.parse(_REG_401)
    assert not m.is_request and m.status == 401 and m.reason == "Unauthorized"
    assert m.header("call-id") == "cid-1@hydrahive"
    assert m.header("CSeq") == "1 REGISTER"
    assert m.header("www-authenticate").startswith("Digest ")
    assert m.header("fehlt") is None


def test_kurzformen_und_mehrfache_kopfzeilen() -> None:
    from backend.sip import message

    raw = (b"INVITE sip:hydra@192.168.178.20:5070 SIP/2.0\r\n"
           b"v: SIP/2.0/UDP 192.168.178.1:5060;branch=z9hG4bK1\r\n"
           b"Via: SIP/2.0/UDP 10.0.0.1;branch=z9hG4bK2\r\n"
           b"f: <sip:0301234@fritz.box>;tag=a\r\nt: <sip:hydra@fritz.box>\r\ni: inv-1\r\n"
           b"CSeq: 7 INVITE\r\nl: 0\r\n\r\n")
    m = message.parse(raw)
    assert m.is_request and m.method == "INVITE" and m.uri == "sip:hydra@192.168.178.20:5070"
    assert m.headers_all("via") == ["SIP/2.0/UDP 192.168.178.1:5060;branch=z9hG4bK1",
                                    "SIP/2.0/UDP 10.0.0.1;branch=z9hG4bK2"]
    assert m.header("from").startswith("<sip:0301234") and m.header("call-id") == "inv-1"


@pytest.mark.parametrize("raw", [
    b"", b"\r\n\r\n", b"Hallo Welt\r\n\r\n", b"SIP/2.0 abc OK\r\n\r\n", b"INVITE\r\n\r\n",
    b"SIP/2.0 200 OK\r\nKaputt ohne Doppelpunkt\r\n\r\n", b"X" * 70000,
])
def test_kaputtes_wird_abgelehnt(raw: bytes) -> None:
    from backend.sip import message

    with pytest.raises(message.ParseError):
        message.parse(raw)


def test_anfrage_bauen_mit_content_length() -> None:
    from backend.sip import message

    raw = message.build_request("REGISTER", "sip:fritz.box", [("Via", "SIP/2.0/UDP 1.2.3.4:5070;branch=z9hG4bKx"),
                                                              ("CSeq", "1 REGISTER")])
    assert raw.startswith(b"REGISTER sip:fritz.box SIP/2.0\r\n")
    assert raw.endswith(b"Content-Length: 0\r\n\r\n")
    assert message.parse(raw).header("cseq") == "1 REGISTER"


def test_kopfzeilen_mit_zeilenumbruch_verboten() -> None:
    from backend.sip import message

    with pytest.raises(ValueError):
        message.build_request("REGISTER", "sip:fritz.box", [("From", "a\r\nVia: evil")])


def test_antwort_auf_anfrage_uebernimmt_pflichtfelder() -> None:
    from backend.sip import message

    inv = message.parse(b"INVITE sip:h@1.2.3.4 SIP/2.0\r\nVia: SIP/2.0/UDP 192.168.178.1:5060;branch=z9hG4bK1\r\n"
                        b"From: <sip:a@fritz.box>;tag=a\r\nTo: <sip:h@fritz.box>\r\nCall-ID: inv-1\r\n"
                        b"CSeq: 7 INVITE\r\nContent-Length: 0\r\n\r\n")
    out = message.parse(message.build_response(inv, 480, "Temporarily Unavailable", to_tag="hh1"))
    assert out.status == 480
    assert out.header("via") == "SIP/2.0/UDP 192.168.178.1:5060;branch=z9hG4bK1"
    assert out.header("call-id") == "inv-1" and out.header("cseq") == "7 INVITE"
    assert out.header("to") == "<sip:h@fritz.box>;tag=hh1"
    assert [k for k, _ in out.headers][:5] == ["via", "from", "to", "call-id", "cseq"]


# ---- Digest ----

def test_rfc2617_beispiel() -> None:
    from backend.sip import digest

    ch = digest.parse_challenge('Digest realm="testrealm@host.com", qop="auth,auth-int", '
                                'nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41"')
    value = digest.authorization(ch, "GET", "/dir/index.html", "Mufasa", "Circle Of Life",
                                 cnonce="0a4f113b", nc=1)
    assert 'response="6629fae49393a05397450978507c4ef1"' in value
    assert "qop=auth," in value and "nc=00000001" in value and 'cnonce="0a4f113b"' in value
    assert 'opaque="5ccc069c403ebaf9f0171e9517f40e41"' in value


def test_ohne_qop_wie_fritzbox() -> None:
    import hashlib

    from backend.sip import digest

    ch = digest.parse_challenge('Digest realm="fritz.box", nonce="ABCDEF0123", algorithm=MD5')
    value = digest.authorization(ch, "REGISTER", "sip:fritz.box", "hydra-telefon", "Sehr-Geheim-42")
    ha1 = hashlib.md5(b"hydra-telefon:fritz.box:Sehr-Geheim-42").hexdigest()
    ha2 = hashlib.md5(b"REGISTER:sip:fritz.box").hexdigest()
    assert f'response="{hashlib.md5(f"{ha1}:ABCDEF0123:{ha2}".encode()).hexdigest()}"' in value
    assert "qop" not in value and "Sehr-Geheim-42" not in value


def test_sha256() -> None:
    import hashlib

    from backend.sip import digest

    ch = digest.parse_challenge('Digest realm="r", nonce="n", algorithm=SHA-256')
    value = digest.authorization(ch, "REGISTER", "sip:x", "u", "p")
    ha1 = hashlib.sha256(b"u:r:p").hexdigest()
    ha2 = hashlib.sha256(b"REGISTER:sip:x").hexdigest()
    assert f'response="{hashlib.sha256(f"{ha1}:n:{ha2}".encode()).hexdigest()}"' in value
    assert "algorithm=SHA-256" in value


@pytest.mark.parametrize("value", [
    'Basic realm="x"', 'Digest realm="r"', 'Digest nonce="n"', 'Digest realm="r", nonce="n", algorithm=MD5-sess',
    'Digest realm="r", nonce="n", qop="auth-int"',
])
def test_nicht_unterstuetzte_challenge(value: str) -> None:
    from backend.sip import digest

    with pytest.raises(digest.Unsupported):
        digest.authorization(digest.parse_challenge(value), "REGISTER", "sip:x", "u", "p")


def test_anfuehrungszeichen_in_challenge_werden_nicht_durchgereicht() -> None:
    from backend.sip import digest

    ch = digest.parse_challenge('Digest realm="r\\"x", nonce="n\r\nVia: evil"')
    with pytest.raises(digest.Unsupported):
        digest.authorization(ch, "REGISTER", "sip:x", "u", "p")
