"""M1 Schritt 10: Verbindungstest – Fehlerarten (auth/tls/connect), Passwort geschwärzt, Verbindung geschlossen."""
from __future__ import annotations

import imaplib
import ssl

import pytest

BASE = {"label": "Privat", "address": "till@example.net", "imap_host": "imap.example.net", "imap_port": 993,
        "imap_tls": "ssl", "smtp_host": "smtp.example.net", "smtp_port": 465, "smtp_tls": "ssl",
        "username": "till@example.net", "password": "geheim-123"}


class _Conn:
    def __init__(self, login_exc=None):
        self.login_exc, self.closed = login_exc, False

    def login(self, u, p):
        if self.login_exc:
            raise self.login_exc
        return "OK", [b""]

    def list(self, *a):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"']

    def logout(self):
        self.closed = True


@pytest.mark.parametrize("exc, code", [
    (imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials"), "auth"),
    (ssl.SSLCertVerificationError("certificate verify failed"), "tls"),
    (TimeoutError("timed out"), "connect"),
    (ConnectionResetError("reset"), "connect"),
])
def test_verbindungstest_unterscheidet_fehler(monkeypatch, exc, code):
    """Zertifikatsfehler oder Zeitüberschreitung sind kein „falsches Passwort“ – die Meldung muss stimmen."""
    from backend import accounts, imap_conn
    conn = _Conn(login_exc=exc)
    monkeypatch.setattr(imap_conn, "open_connection", lambda acc, **kw: conn)
    with pytest.raises(accounts.ConnectError) as e:
        accounts._test_login(BASE, "pw")
    assert e.value.code == code and conn.closed


@pytest.mark.parametrize("exc, code", [(ssl.SSLError("wrong version"), "tls"),
                                       (OSError("Connection refused"), "connect")])
def test_verbindungsaufbau_fehler(monkeypatch, exc, code):
    from backend import accounts, imap_conn

    def boom(acc, **kw):
        raise exc
    monkeypatch.setattr(imap_conn, "open_connection", boom)
    with pytest.raises(accounts.ConnectError) as e:
        accounts._test_login(BASE, "pw")
    assert e.value.code == code


def test_verbindungstest_ok_meldet_ordner(monkeypatch):
    from backend import accounts, imap_conn
    monkeypatch.setattr(imap_conn, "open_connection", lambda acc, **kw: _Conn())
    assert accounts._test_login(BASE, "pw") == {"folders": 1}



def test_verbindungstest_schwaerzt_passwort(monkeypatch):
    from backend import accounts, imap_conn
    import imaplib

    class Leak(_Conn):
        def login(self, u, p):
            raise imaplib.IMAP4.error(f"LOGIN {u} {p} rejected")
    monkeypatch.setattr(imap_conn, "open_connection", lambda acc, **kw: Leak())
    with pytest.raises(accounts.ConnectError) as e:
        accounts._test_login(BASE, "geheim-123")
    assert "geheim-123" not in str(e.value) and "***" in str(e.value)
