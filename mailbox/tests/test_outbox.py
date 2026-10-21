"""M2 Schritt 5: Senden als Ablauf – Grenze, Versand, Archivkopie, Ablage im Gesendet-Ordner (nicht bei Gmail).

Grundsatz: Ist die Mail per SMTP raus, meldet der Ablauf „gesendet“ – egal was danach scheitert (sonst sendet der
Nutzer ein zweites Mal). Die Archivkopie entsteht vor der Server-Ablage (das Archiv ist das Backup).
"""
from __future__ import annotations

import ssl

import pytest
from _fake_imap import FakeIMAP, FakeServer
from _fake_smtp import SMTPServer, make_ca

ACC = {"id": "acc1", "address": "till@example.net", "sender_name": "Till", "signature": "", "username": "till@example.net",
       "imap_host": "imap.example.net", "smtp_host": "localhost", "smtp_tls": "ssl"}


@pytest.fixture
def smtp(tmp_path, monkeypatch):
    from backend import netcheck, smtp_send
    certs = make_ca(tmp_path, "localhost")
    monkeypatch.setattr(smtp_send, "_context", lambda: ssl.create_default_context(cafile=str(certs["ca"])))
    real = netcheck.check
    monkeypatch.setattr(netcheck, "MAIL_PORTS", frozenset(range(1, 65536)))
    monkeypatch.setattr(smtp_send.netcheck, "check", lambda h, p, **kw: real(h, p, resolve=lambda _h: ["127.0.0.1"], **kw))
    srv = SMTPServer(certs, mode="ssl")
    yield srv
    srv.close()


@pytest.fixture
def imap():
    s = FakeServer()
    s.box("Gesendet", special="\\Sent")
    return s


def _acc(smtp, **kw):
    return {**ACC, "smtp_port": smtp.port, **kw}


def _known_folders(imap_server, acc):
    from backend import fetch
    fetch.sync_account(acc, FakeIMAP(imap_server))


def _deliver(acc, imap_server, **kw):
    from backend import compose, outbox
    built = compose.build(acc, to="Anna <anna@example.org>", bcc="geheim@x.de", subject="Hallo", text="Hi")
    return built, outbox.deliver(acc, "pw", built, allow_internal={"localhost"},
                                 open_imap=lambda a: FakeIMAP(imap_server), **kw)


def _index(where="1=1", args=()):
    from backend import index_db
    with index_db.connect() as c:
        return [dict(r) for r in c.execute(f"SELECT m.*, f.name AS folder FROM messages m JOIN folders f "
                                           f"ON f.id=m.folder_id WHERE {where}", args)]


def test_senden_ablegen_archivieren(archive, smtp, imap):
    from backend import archive as arch
    acc = _acc(smtp)
    _known_folders(imap, acc)
    built, r = _deliver(acc, imap)
    assert r["sent"] and r["sent_copy"] == "server" and r["message_id"] == built.message_id
    assert smtp.received[0]["rcpt"] == ["anna@example.org", "geheim@x.de"]
    box = imap.boxes["Gesendet"]
    assert [(raw, fl) for raw, fl in box.msgs.values()] == [(built.raw, {"\\Seen"})]
    rows = _index()
    assert len(rows) == 1 and rows[0]["folder"] == "Gesendet" and rows[0]["message_id"] == built.message_id
    assert arch.read(rows[0]["path"]) == built.raw
    assert rows[0]["deleted_on_server"] == 0, "auf dem Server abgelegt – nicht als „nur im Archiv“ zeigen"


def test_abgleich_danach_keine_doppelte(archive, smtp, imap):
    """Die abgelegte Kopie kommt beim nächsten Abgleich als dieselbe Mail an (gleiche Bytes) – kein Duplikat."""
    acc = _acc(smtp)
    _known_folders(imap, acc)
    _deliver(acc, imap)
    _known_folders(imap, acc)
    rows = _index()
    assert len(rows) == 1 and rows[0]["deleted_on_server"] == 0


def test_gmail_legt_selbst_ab(archive, smtp, imap):
    acc = _acc(smtp, imap_host="imap.gmail.com")
    _known_folders(imap, acc)
    _, r = _deliver(acc, imap)
    assert r["sent"] and r["sent_copy"] == "provider" and imap.appends == [] and _index() == []


def test_ablage_scheitert_mail_trotzdem_gesendet(archive, smtp, imap):
    acc = _acc(smtp)
    _known_folders(imap, acc)
    imap.fail_append = True
    built, r = _deliver(acc, imap)
    assert r["sent"] and r["sent_copy"] == "archive_only" and "OVERQUOTA" in r["warning"]
    assert len(smtp.received) == 1
    rows = _index()
    assert len(rows) == 1 and rows[0]["deleted_on_server"] == 1, "nur im Archiv – ehrlich markiert"


def test_imap_nicht_erreichbar_mail_trotzdem_gesendet(archive, smtp, imap):
    from backend import compose, outbox
    acc = _acc(smtp)
    _known_folders(imap, acc)

    def boom(a):
        raise OSError("Connection refused")
    built = compose.build(acc, to="a@x.de", subject="s", text="x")
    r = outbox.deliver(acc, "pw", built, allow_internal={"localhost"}, open_imap=boom)
    assert r["sent"] and r["sent_copy"] == "archive_only" and len(_index()) == 1


def test_ohne_gesendet_ordner_nur_archiv(archive, smtp):
    s = FakeServer()                    # nur INBOX
    acc = _acc(smtp)
    _known_folders(s, acc)
    _, r = _deliver(acc, s)
    assert r["sent"] and r["sent_copy"] == "archive_only" and s.appends == []
    assert len(_index()) == 1


def test_versand_scheitert_nichts_abgelegt_nichts_gezaehlt(archive, smtp, imap):
    from backend import outbox, smtp_send
    from hydrahive.db.connection import db
    acc = _acc(smtp)
    _known_folders(imap, acc)
    with pytest.raises(smtp_send.SendError):
        from backend import compose
        outbox.deliver(acc, "falsch", compose.build(acc, to="a@x.de", subject="s", text="x"),
                       allow_internal={"localhost"}, open_imap=lambda a: FakeIMAP(imap))
    assert imap.appends == [] and _index() == []
    with db() as c:
        assert c.execute("SELECT COUNT(*) FROM module_mailbox_sendlog").fetchone()[0] == 0


def test_grenze_vor_dem_versand(archive, smtp, imap, monkeypatch):
    from backend import outbox, ratelimit
    monkeypatch.setenv("HH_MAILBOX_SEND_PER_HOUR", "1")
    acc = _acc(smtp)
    _deliver(acc, imap)
    with pytest.raises(ratelimit.RateLimited):
        _deliver(acc, imap)
    assert len(smtp.received) == 1
    assert outbox                          # Modul geladen


def test_fehler_nach_dem_versand_meldet_gesendet(archive, smtp, imap, monkeypatch):
    """Selbst wenn Zählung und Archiv scheitern: gesendet ist gesendet (kein zweiter Versand durch den Nutzer)."""
    from backend import archive as arch
    from backend import ratelimit
    acc = _acc(smtp)

    def boom(*a, **kw):
        raise RuntimeError("Platte voll")
    monkeypatch.setattr(ratelimit, "record", boom)
    monkeypatch.setattr(arch, "store", boom)
    _, r = _deliver(acc, imap)
    assert r["sent"] and len(smtp.received) == 1 and "Platte voll" in r["warning"]


def test_teilweise_abgelehnt_wird_gemeldet(archive, tmp_path, monkeypatch, imap):
    from backend import compose, netcheck, outbox, smtp_send
    certs = make_ca(tmp_path, "localhost")
    monkeypatch.setattr(smtp_send, "_context", lambda: ssl.create_default_context(cafile=str(certs["ca"])))
    real = netcheck.check
    monkeypatch.setattr(netcheck, "MAIL_PORTS", frozenset(range(1, 65536)))
    monkeypatch.setattr(smtp_send.netcheck, "check", lambda h, p, **kw: real(h, p, resolve=lambda _h: ["127.0.0.1"], **kw))
    srv = SMTPServer(certs, mode="ssl", reject={"weg@x.de"})
    try:
        acc = _acc(srv)
        r = outbox.deliver(acc, "pw", compose.build(acc, to="a@x.de, weg@x.de", subject="s", text="x"),
                           allow_internal={"localhost"}, open_imap=lambda a: FakeIMAP(imap))
        assert r["sent"] and r["refused"] == ["weg@x.de"]
    finally:
        srv.close()
