"""M2 Schritt 3: Versand – TLS Pflicht, Zertifikat geprüft, geprüfte IP, Fehlerarten, Passwort geschwärzt.

Läuft gegen einen echten SMTP-Server im Test (tests/_fake_smtp.py) mit eigener Test-CA.
"""
from __future__ import annotations

import ssl

import pytest
from _fake_smtp import SMTPServer, make_ca

RAW = b"From: till@example.net\r\nTo: a@x.de\r\nSubject: s\r\n\r\n.Punkt am Zeilenanfang\r\nHallo\r\n"


@pytest.fixture
def certs(tmp_path):
    return make_ca(tmp_path, "localhost")


@pytest.fixture
def trust(monkeypatch, certs):
    """Die Test-CA vertrauen (wie eine echte öffentliche CA) und localhost als geprüfte Adresse durchlassen."""
    from backend import smtp_send
    monkeypatch.setattr(smtp_send, "_context", lambda: ssl.create_default_context(cafile=str(certs["ca"])))
    _local(monkeypatch)
    return certs


def _local(monkeypatch):
    """Test-Server lauscht auf 127.0.0.1; localhost kann zuerst ::1 liefern → Auflösung im Test festlegen."""
    from backend import netcheck, smtp_send
    real = netcheck.check
    monkeypatch.setattr(netcheck, "MAIL_PORTS", frozenset(range(1, 65536)))
    monkeypatch.setattr(smtp_send.netcheck, "check",
                        lambda h, p, **kw: real(h, p, resolve=lambda _h: ["127.0.0.1"], **kw))


def _acc(srv, tls):
    return {"id": "a1", "address": "till@example.net", "smtp_host": "localhost", "smtp_port": srv.port, "smtp_tls": tls,
            "username": "till@example.net"}


@pytest.mark.parametrize("mode", ["ssl", "starttls"])
def test_senden_ok(trust, mode):
    from backend import smtp_send
    srv = SMTPServer(trust, mode=mode)
    try:
        smtp_send.send(_acc(srv, mode), "pw", RAW, ["a@x.de", "geheim@x.de"], allow_internal={"localhost"})
        got = srv.received[0]
        assert got["from"] == "till@example.net" and got["rcpt"] == ["a@x.de", "geheim@x.de"]
        assert b".Punkt am Zeilenanfang" in got["data"] and not srv.plain_auth_seen
    finally:
        srv.close()


def test_kein_starttls_angebot_kein_klartext(trust):
    """Server ohne STARTTLS: abbrechen, nie Passwort im Klartext senden."""
    from backend import smtp_send
    srv = SMTPServer(trust, mode="plain")
    try:
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(_acc(srv, "starttls"), "pw", RAW, ["a@x.de"], allow_internal={"localhost"})
        assert e.value.code == "tls" and not srv.plain_auth_seen and srv.received == []
    finally:
        srv.close()


@pytest.mark.parametrize("mode", ["ssl", "starttls"])
def test_fremdes_zertifikat_abgelehnt(monkeypatch, certs, mode):
    """Ohne Vertrauen in die CA (= selbst signiert / falscher Server): kein Versand."""
    from backend import smtp_send
    _local(monkeypatch)
    srv = SMTPServer(certs, mode=mode)
    try:
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(_acc(srv, mode), "pw", RAW, ["a@x.de"], allow_internal={"localhost"})
        assert e.value.code == "tls" and srv.received == [] and not srv.plain_auth_seen
    finally:
        srv.close()


def test_falscher_hostname_abgelehnt(monkeypatch, tmp_path):
    """Zertifikat gilt für einen anderen Namen → Ablehnung, obwohl die CA vertraut ist."""
    from backend import smtp_send
    certs = make_ca(tmp_path, "anderer.example")
    monkeypatch.setattr(smtp_send, "_context", lambda: ssl.create_default_context(cafile=str(certs["ca"])))
    _local(monkeypatch)
    srv = SMTPServer(certs, mode="ssl")
    try:
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(_acc(srv, "ssl"), "pw", RAW, ["a@x.de"], allow_internal={"localhost"})
        assert e.value.code == "tls"
    finally:
        srv.close()


def test_falsches_passwort_geschwaerzt(trust):
    from backend import smtp_send
    srv = SMTPServer(trust, mode="ssl")
    try:
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(_acc(srv, "ssl"), "falsch-geheim", RAW, ["a@x.de"], allow_internal={"localhost"})
        assert e.value.code == "auth" and "falsch-geheim" not in str(e.value) and srv.received == []
    finally:
        srv.close()


def test_empfaenger_abgelehnt(trust):
    from backend import smtp_send
    srv = SMTPServer(trust, mode="ssl", reject={"weg@x.de"})
    try:
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(_acc(srv, "ssl"), "pw", RAW, ["weg@x.de"], allow_internal={"localhost"})
        assert e.value.code == "rejected" and "weg@x.de" in str(e.value)
    finally:
        srv.close()


def test_teilweise_abgelehnt_meldet_aber_sendet(trust):
    from backend import smtp_send
    srv = SMTPServer(trust, mode="ssl", reject={"weg@x.de"})
    try:
        r = smtp_send.send(_acc(srv, "ssl"), "pw", RAW, ["a@x.de", "weg@x.de"], allow_internal={"localhost"})
        assert r == {"refused": ["weg@x.de"]} and srv.received[0]["rcpt"] == ["a@x.de"]
    finally:
        srv.close()


def test_interne_adresse_ohne_freigabe(trust):
    from backend import smtp_send
    srv = SMTPServer(trust, mode="ssl")
    try:
        with pytest.raises(smtp_send.SendError) as e:
            smtp_send.send(_acc(srv, "ssl"), "pw", RAW, ["a@x.de"])
        assert e.value.code == "blocked" and srv.received == []
    finally:
        srv.close()


def test_nicht_erreichbar():
    from backend import smtp_send
    acc = {"address": "a@x.de", "smtp_host": "127.0.0.1", "smtp_port": 465, "smtp_tls": "ssl", "username": "u"}
    with pytest.raises(smtp_send.SendError) as e:
        smtp_send.send(acc, "pw", RAW, ["a@x.de"], allow_internal={"127.0.0.1"})
    assert e.value.code == "connect"


def test_ohne_smtp_server_im_konto():
    from backend import smtp_send
    with pytest.raises(smtp_send.SendError) as e:
        smtp_send.send({"address": "a@x.de", "smtp_host": "", "smtp_port": 465, "smtp_tls": "ssl", "username": "u"},
                       "pw", RAW, ["a@x.de"])
    assert e.value.code == "config"


def test_kontext_prueft_zertifikat():
    """Der echte Kontext (nicht der Test-Ersatz) prüft Zertifikat und Hostnamen, TLS ≥ 1.2."""
    from backend import smtp_send
    ctx = smtp_send._context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2


@pytest.mark.parametrize("mode", ["ssl", "starttls"])
def test_verbindet_mit_gepruefter_ip_nicht_mit_dem_namen(monkeypatch, tmp_path, mode):
    """Der Name „mail.test“ ist nicht auflösbar (RFC 6761). Geht der Versand trotzdem, wurde mit der geprüften IP
    verbunden – und das Zertifikat trotzdem gegen den Namen geprüft (kein DNS-Rebinding zwischen Prüfung und Verbindung)."""
    from backend import netcheck, smtp_send
    certs = make_ca(tmp_path, "mail.test")
    monkeypatch.setattr(smtp_send, "_context", lambda: ssl.create_default_context(cafile=str(certs["ca"])))
    real = netcheck.check
    monkeypatch.setattr(netcheck, "MAIL_PORTS", frozenset(range(1, 65536)))
    monkeypatch.setattr(smtp_send.netcheck, "check",
                        lambda h, p, **kw: real(h, p, resolve=lambda _h: ["127.0.0.1"], **kw))
    srv = SMTPServer(certs, mode=mode)
    try:
        acc = {**_acc(srv, mode), "smtp_host": "mail.test"}
        smtp_send.send(acc, "pw", RAW, ["a@x.de"], allow_internal={"mail.test"})
        assert len(srv.received) == 1
    finally:
        srv.close()
