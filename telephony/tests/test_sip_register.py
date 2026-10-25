"""Ein Anmeldevorgang gegen einen echten UDP-Registrar (RFC 3261 §10)."""
from __future__ import annotations

import socket

import pytest
from _fake_registrar import FakeRegistrar


@pytest.fixture
def sock():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    yield s
    s.close()


def _state(reg: FakeRegistrar, sock, **over):
    from backend.sip.register import RegState

    d = {"user": "hydra-telefon", "password": "Sehr-Geheim-42", "domain": "fritz.box",
         "target": ("127.0.0.1", reg.port), "local": sock.getsockname(), "display_name": "HydraHive"}
    d.update(over)
    return RegState(**d)


@pytest.fixture
def reg():
    r = FakeRegistrar()
    yield r
    r.close()


def test_anmeldung_mit_challenge(reg, sock) -> None:
    from backend.sip.register import register

    st = _state(reg, sock)
    out = register(sock, st, 300, timeout=3)
    assert out.code == "registered" and out.expires == 300
    regs = reg.registers()
    assert len(regs) == 2 and "authorization" not in dict(regs[0].headers)
    assert regs[1].header("authorization").startswith("Digest ")
    assert regs[0].header("call-id") == regs[1].header("call-id")
    assert [m.header("cseq") for m in regs] == ["1 REGISTER", "2 REGISTER"]
    assert regs[0].uri == "sip:fritz.box"
    assert regs[0].header("to") == "<sip:hydra-telefon@fritz.box>"
    assert regs[0].header("from").startswith('"HydraHive" <sip:hydra-telefon@fritz.box>;tag=')
    assert ";rport" in regs[0].header("via") and ";branch=z9hG4bK" in regs[0].header("via")
    assert regs[0].header("via").split(";branch=")[1] != regs[1].header("via").split(";branch=")[1]


def test_kennwort_geht_nie_im_klartext_raus(reg, sock) -> None:
    from backend.sip.register import register

    register(sock, _state(reg, sock), 300, timeout=3)
    for m in reg.requests:
        assert "Sehr-Geheim-42" not in str(m.headers) and b"Sehr-Geheim-42" not in m.body


def test_erneute_anmeldung_gleiche_call_id_hoehere_cseq(reg, sock) -> None:
    from backend.sip.register import register

    st = _state(reg, sock)
    register(sock, st, 300, timeout=3)
    register(sock, st, 300, timeout=3)
    regs = reg.registers()
    assert len({m.header("call-id") for m in regs}) == 1
    nums = [int(m.header("cseq").split()[0]) for m in regs]
    assert nums == sorted(nums) and len(set(nums)) == len(nums)


def test_falsches_kennwort(reg, sock) -> None:
    from backend.sip.register import register

    out = register(sock, _state(reg, sock, password="Falsch-Falsch-1"), 300, timeout=3)
    assert out.code == "auth_failed"


def test_zweite_challenge_nach_anmeldung_ist_auth_failed(sock) -> None:
    """Manche Anlagen antworten auf falsche Daten erneut mit 401 statt 403 – dann nicht endlos weiter."""
    r = FakeRegistrar(rechallenge=True)
    try:
        from backend.sip.register import register

        out = register(sock, _state(r, sock), 300, timeout=3)
        assert out.code == "auth_failed" and out.status == 401
        assert len(r.registers()) == 2
    finally:
        r.close()


def test_falscher_benutzer(reg, sock) -> None:
    from backend.sip.register import register

    assert register(sock, _state(reg, sock, user="unbekannt-1"), 300, timeout=3).code == "auth_failed"


@pytest.mark.parametrize("code,expected", [(404, "not_found"), (403, "auth_failed"), (503, "rejected"),
                                           (500, "rejected"), (480, "rejected")])
def test_feste_antworten(sock, code: int, expected: str) -> None:
    from backend.sip.register import register

    r = FakeRegistrar(fixed=code)
    try:
        assert register(sock, _state(r, sock), 300, timeout=3).code == expected
    finally:
        r.close()


def test_keine_antwort_wiederholt_dann_unreachable(sock) -> None:
    from backend.sip.register import register

    r = FakeRegistrar(silent=True)
    try:
        out = register(sock, _state(r, sock), 300, timeout=1.6)
        assert out.code == "unreachable"
        assert len(r.registers()) >= 3, "Wiederholung nach RFC 3261 §17.1.2 (T1 = 0,5 s, verdoppelnd)"
    finally:
        r.close()


def test_mindest_ablaufzeit_423(sock) -> None:
    from backend.sip.register import register

    r = FakeRegistrar(min_expires=600)
    try:
        out = register(sock, _state(r, sock), 300, timeout=3)
        assert out.code == "registered" and out.expires == 600
    finally:
        r.close()


def test_kuerzere_ablaufzeit_vom_server_wird_uebernommen(sock) -> None:
    from backend.sip.register import register

    r = FakeRegistrar(max_expires=120)
    try:
        assert register(sock, _state(r, sock), 300, timeout=3).expires == 120
    finally:
        r.close()


def test_abmelden(reg, sock) -> None:
    from backend.sip.register import register

    st = _state(reg, sock)
    register(sock, st, 300, timeout=3)
    out = register(sock, st, 0, timeout=3)
    assert out.code == "registered" and out.expires == 0
    assert reg.registers()[-1].header("expires") == "0"
    assert set(reg.bindings.values()) == {0}


def test_hinter_router_wird_gelernte_adresse_als_contact_genutzt(sock) -> None:
    """NAT: Die Anlage sieht uns unter anderer Adresse (Via received/rport). Anrufe müssen dorthin."""
    from backend.sip.register import register

    r = FakeRegistrar(nat=("192.168.3.50", 40123))
    try:
        st = _state(r, sock)
        assert register(sock, st, 300, timeout=3).code == "registered"
        assert "@192.168.3.50:40123" in r.registers()[-1].header("contact")
        old = f"<sip:hydra-telefon@127.0.0.1:{sock.getsockname()[1]}>"
        assert r.bindings == {old: 0, "<sip:hydra-telefon@192.168.3.50:40123>": 300}, "alte Adresse abgemeldet"
        assert st.contact == ("192.168.3.50", 40123)
    finally:
        r.close()


def test_antwort_von_fremder_adresse_wird_ignoriert(sock) -> None:
    from backend.sip import message
    from backend.sip.register import register

    r = FakeRegistrar(silent=True)
    evil = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    evil.bind(("127.0.0.1", 0))
    try:
        st = _state(r, sock)
        import threading

        def spoof():
            import time
            time.sleep(0.2)
            req = r.registers()[0]
            evil.sendto(message.build_response(req, 200, "OK", to_tag="x",
                                               extra=[("Contact", "<sip:x@1.2.3.4>;expires=300")]),
                        sock.getsockname())
        threading.Thread(target=spoof, daemon=True).start()
        assert register(sock, st, 300, timeout=1.0).code == "unreachable"
    finally:
        evil.close()
        r.close()


def test_fremde_anfragen_waehrend_der_anmeldung_werden_weitergereicht(reg, sock) -> None:
    from backend.sip import message
    from backend.sip.register import register

    got = []
    st = _state(reg, sock)
    reg.send(message.build_request("OPTIONS", "sip:h@127.0.0.1", [
        ("Via", "SIP/2.0/UDP 127.0.0.1:1;branch=z9hG4bKo"), ("From", "<sip:a@b>;tag=1"), ("To", "<sip:h@b>"),
        ("Call-ID", "opt-1"), ("CSeq", "1 OPTIONS")]), sock.getsockname())
    out = register(sock, st, 300, timeout=3, on_request=lambda m, a: got.append(m.method))
    assert out.code == "registered" and got == ["OPTIONS"]


def test_anfragen_von_fremden_adressen_werden_verworfen(reg, sock) -> None:
    from backend.sip import message
    from backend.sip.register import register

    got = []
    other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    other.bind(("127.0.0.1", 0))
    try:
        other.sendto(message.build_request("INVITE", "sip:h@127.0.0.1", [
            ("Via", "SIP/2.0/UDP 127.0.0.1:1;branch=z9hG4bKo"), ("From", "<sip:a@b>;tag=1"), ("To", "<sip:h@b>"),
            ("Call-ID", "inv-x"), ("CSeq", "1 INVITE")]), sock.getsockname())
        out = register(sock, _state(reg, sock), 300, timeout=3, on_request=lambda m, a: got.append(m.method))
        assert out.code == "registered" and got == []
    finally:
        other.close()


def test_proxy_anmeldung_407_nutzt_proxy_authorization(sock) -> None:
    from backend.sip import message
    from backend.sip.register import register

    r = FakeRegistrar(silent=True)
    try:
        st = _state(r, sock)
        import threading

        def answer():
            import time
            for _ in range(200):
                if r.registers():
                    break
                time.sleep(0.01)
            r.send(message.build_response(r.registers()[0], 407, "Proxy Authentication Required", to_tag="s",
                                          extra=[("Proxy-Authenticate", 'Digest realm="fritz.box", nonce="P1"')]),
                   sock.getsockname())
        threading.Thread(target=answer, daemon=True).start()
        register(sock, st, 300, timeout=1.5)
        second = [m for m in r.registers() if m.header("cseq") == "2 REGISTER"]
        assert second and second[0].header("proxy-authorization", ).startswith("Digest ")
        assert second[0].header("authorization") is None
    finally:
        r.close()
