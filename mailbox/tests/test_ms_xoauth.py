"""M1b: Anmeldung an IMAP und SMTP per XOAUTH2 – nur über auth_login, Token nur an Microsoft-Server."""
# ruff: noqa: F811 - pytest-Fixtures aus _ms_base
from __future__ import annotations

import imaplib
import re
import smtplib
from pathlib import Path

import pytest
from _fake_imap import FakeIMAP, FakeServer
from _ms_base import _ms_state, app_set, clock, err, ms  # noqa: F401
from test_ms_login import ADDR, _ms_account


def test_imap_xoauth2(ms, clock, app_set):
    from backend import auth_login
    acc = _ms_account()
    assert acc["imap_host"] in auth_login.MS_IMAP
    srv = FakeServer(user=ADDR, password="egal")
    conn = FakeIMAP(srv)
    auth_login.imap_login(conn, acc)
    assert srv.xoauth == [("XOAUTH2", f"user={ADDR}\x01auth=Bearer AT-1\x01\x01".encode())] and conn.logged_in


def test_imap_abgelehnt_token_verworfen_und_geschwaerzt(ms, clock, app_set):
    from backend import auth_login
    acc = _ms_account()
    srv = FakeServer(user=ADDR)
    srv.token = "ANDERS"
    with pytest.raises(imaplib.IMAP4.error) as e:
        auth_login.imap_login(FakeIMAP(srv), acc)
    assert "AT-1" not in str(e.value)
    srv.token = "AT-2"
    ms.token.append((200, {"access_token": "AT-2", "expires_in": 3600}))
    auth_login.imap_login(FakeIMAP(srv), acc)        # abgelehnter Token wird nicht wiederverwendet


def test_imap_abgelaufen_wird_imap_fehler(ms, clock, app_set):
    from backend import auth_login
    acc = _ms_account()
    ms.token.append(err("invalid_grant"))
    with pytest.raises(imaplib.IMAP4.error, match="erneut"):
        auth_login.imap_login(FakeIMAP(FakeServer(user=ADDR)), acc)


def test_imap_netz_weg_wird_verbindungsfehler(ms, clock, app_set):
    from backend import auth_login
    ms.fail_network = True
    with pytest.raises(OSError):
        auth_login.imap_login(FakeIMAP(FakeServer(user=ADDR)), _ms_account())


def test_imap_passwort_wie_bisher():
    from backend import auth_login
    srv = FakeServer(user="a@x.de", password="pw")
    conn = FakeIMAP(srv)
    auth_login.imap_login(conn, {"id": "x", "address": "a@x.de", "username": "a@x.de", "auth": "password"}, "pw")
    assert conn.logged_in and srv.xoauth == []


def test_smtp_xoauth2(ms, clock, app_set, monkeypatch, tmp_path):
    import ssl

    from _fake_smtp import SMTPServer, make_ca
    from backend import smtp_send
    certs = make_ca(tmp_path, "localhost")
    monkeypatch.setattr(smtp_send, "_context", lambda: ssl.create_default_context(cafile=str(certs["ca"])))
    from backend import netcheck
    real = netcheck.check
    monkeypatch.setattr(netcheck, "MAIL_PORTS", frozenset(range(1, 65536)))
    monkeypatch.setattr(smtp_send.netcheck, "check",
                        lambda h, p, **kw: real(h, p, resolve=lambda _h: ["127.0.0.1"], **kw))
    from backend import auth_login
    monkeypatch.setattr(auth_login, "MS_SMTP", frozenset({"localhost"}))   # Test-Server statt Microsoft
    srv = SMTPServer(certs, mode="starttls", user=ADDR)
    try:
        acc = {**_ms_account(), "smtp_host": "localhost", "smtp_port": srv.port}
        smtp_send.send(acc, "", b"Subject: s\r\n\r\nHallo\r\n", ["b@x.de"], allow_internal={"localhost"})
        assert srv.xoauth == [f"user={ADDR}\x01auth=Bearer AT-1\x01\x01".encode()] and srv.received
        srv.token = "ANDERS"
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(acc, "", b"Subject: s\r\n\r\nHallo\r\n", ["b@x.de"], allow_internal={"localhost"})
        assert e.value.code == "auth" and "AT-1" not in str(e.value)
    finally:
        srv.close()


def test_keine_anmeldung_ausserhalb_von_auth_login():
    """Jede Anmeldung läuft über auth_login – sonst vergisst eine Stelle die Microsoft-Konten."""
    backend = Path(__file__).resolve().parents[1] / "backend"
    bad = [f"{p.name}:{i}" for p in backend.glob("*.py") if p.name != "auth_login.py"
           for i, line in enumerate(p.read_text().splitlines(), 1) if re.search(r"\.(login|authenticate)\(", line)]
    assert bad == []



@pytest.mark.parametrize("field,host", [("imap_host", "imap.boese.example"), ("smtp_host", "smtp.boese.example")])
def test_token_nie_an_fremde_server(ms, clock, app_set, field, host):
    """Ein Microsoft-Token geht nur an Microsoft – auch wenn ein Konto irgendwie einen anderen Server trägt."""
    from backend import auth_login
    acc = {**_ms_account(), field: host}
    with pytest.raises((imaplib.IMAP4.error, smtplib.SMTPException)):
        if field == "imap_host":
            auth_login.imap_login(FakeIMAP(FakeServer(user=ADDR)), acc)
        else:
            auth_login.smtp_login(object(), acc)
    assert ms.calls == [], "nicht einmal ein Token wird geholt"
