"""0.3.0 / Befund Prod 22.10.2026 (Yahoo): Der Server schreibt die abgelegte Gesendet-Kopie um (896 statt 699 Bytes,
X-Mailer/References/Content-Length dazu). Der Abgleich hielt sie für eine andere Mail → doppelt in der Liste, und die
eigene Archivkopie stand fälschlich unter „Nur im Archiv“.

Soll: Eine selbst gesendete Mail erscheint genau einmal (die Fassung vom Server mit Fundort). Die eigene Kopie bleibt
als Datei im Archiv (gelöscht wird nie), wird aber nicht als „Nur im Archiv“ gezeigt, solange die Server-Fassung da ist.
Verschwindet die Server-Fassung, gilt wieder die Archiv-Regel (eine Mail unter „Nur im Archiv“).
"""
from __future__ import annotations

from _fake_imap import FakeIMAP, FakeServer
from _fetch_base import ACC

ACC_S = {**ACC, "imap_host": "imap.mail.yahoo.com", "sender_name": "", "signature": "", "username": "till@example.net"}


def _sent_raw():
    from backend import compose
    return compose.build(ACC_S, to="a@x.de", subject="Test", text="Hallo")


def _rewritten(raw: bytes) -> bytes:
    """Wie Yahoo: zusätzliche Kopfzeilen vorne → andere Bytes, gleiche Message-ID."""
    return b"X-Mailer: WebService/1.1\r\nContent-Length: 403\r\n" + raw


def _sync(srv):
    from backend import fetch
    fetch.sync_account(ACC_S, FakeIMAP(srv))


def _deliver(srv, built, monkeypatch, *, rewrite=True):
    """Senden wie outbox.deliver, nur SMTP ersetzt; die Server-Ablage schreibt um wie Yahoo."""
    from backend import outbox, smtp_send
    monkeypatch.setattr(smtp_send, "send", lambda *a, **kw: {})

    class Rewriting(FakeIMAP):
        def append(self, mailbox, flags, dt, message):
            return super().append(mailbox, flags, dt, _rewritten(message) if rewrite else message)
    return outbox.deliver(ACC_S, "pw", built, open_imap=lambda a: Rewriting(srv))


def _visible(where="1=1"):
    """Was die Liste zeigt (search.search, wie die Route /messages)."""
    from backend import search
    return search.search({ACC_S["id"]: ACC_S["address"]}, "", only_deleted=False, limit=50, offset=0)["items"]


def _only_archive():
    from backend import search
    return search.search({ACC_S["id"]: ACC_S["address"]}, "", only_deleted=True, limit=50, offset=0)["items"]


def _srv():
    s = FakeServer()
    s.box("Sent", special="\\Sent")
    return s


def test_umgeschriebene_kopie_nur_einmal_sichtbar(archive, monkeypatch):
    srv = _srv()
    _sync(srv)
    built = _sent_raw()
    r = _deliver(srv, built, monkeypatch)
    assert r["sent_copy"] == "server"
    _sync(srv)
    sent = [m for m in _visible() if m["subject"] == "Test"]
    assert len(sent) == 1, sent
    assert sent[0]["folder"] == "Sent" and sent[0]["deleted_on_server"] == 0
    assert [m for m in _only_archive() if m["subject"] == "Test"] == []


def test_beide_dateien_bleiben_im_archiv(archive, monkeypatch):
    from backend import archive as arch
    from backend import index_db
    srv = _srv()
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch)
    _sync(srv)
    with index_db.connect() as c:
        paths = [r[0] for r in c.execute("SELECT path FROM messages WHERE message_id=?", (built.message_id,))]
    assert len(paths) == 2
    raws = sorted(arch.read(p) for p in paths)
    assert built.raw in raws and _rewritten(built.raw) in raws


def test_vor_dem_abgleich_sichtbar(archive, monkeypatch):
    """Direkt nach dem Senden (Abgleich noch nicht gelaufen) ist die Mail schon im Gesendet-Ordner sichtbar."""
    srv = _srv()
    _sync(srv)
    _deliver(srv, _sent_raw(), monkeypatch)
    sent = [m for m in _visible() if m["subject"] == "Test"]
    assert len(sent) == 1 and sent[0]["deleted_on_server"] == 0


def test_server_fassung_weg_dann_einmal_nur_im_archiv(archive, monkeypatch):
    """Archiv-Regel bleibt: Löscht der Server die Gesendet-Kopie, steht die Mail EINMAL unter „Nur im Archiv“."""
    srv = _srv()
    _sync(srv)
    _deliver(srv, _sent_raw(), monkeypatch)
    _sync(srv)
    srv.boxes["Sent"].msgs.clear()
    _sync(srv)
    gone = [m for m in _only_archive() if m["subject"] == "Test"]
    assert len(gone) == 1, gone
    assert [m for m in _visible() if m["subject"] == "Test" and m["deleted_on_server"] == 0] == []


def test_ohne_umschreiben_wie_bisher_eine(archive, monkeypatch):
    srv = _srv()
    _sync(srv)
    _deliver(srv, _sent_raw(), monkeypatch, rewrite=False)
    _sync(srv)
    assert len([m for m in _visible() if m["subject"] == "Test"]) == 1


def test_fremde_mail_mit_gleicher_message_id_nicht_versteckt(archive, monkeypatch):
    """Nur die selbst gesendete Kopie wird zurückgestellt – eine empfangene Mail mit (gefälschter) gleicher
    Message-ID im Posteingang verdeckt nichts und wird nicht versteckt."""
    srv = _srv()
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch)
    srv.boxes["INBOX"].add(b"From: boese@x.de\r\nSubject: Falle\r\nMessage-ID: " + built.message_id.encode() + b"\r\n\r\nx")
    _sync(srv)
    subjects = sorted(m["subject"] for m in _visible())
    assert subjects == ["Falle", "Test"], subjects


def test_altlast_aufraeumen(archive, monkeypatch):
    """Bestand aus 0.2.0 (eigene Kopie ohne Kennzeichen, steht unter „Nur im Archiv“, Server-Fassung im Gesendet-Ordner
    mit gleicher Message-ID): nach dem Abgleich nur noch einmal sichtbar, nicht mehr unter „Nur im Archiv“."""
    from backend import index_db
    srv = _srv()
    _sync(srv)
    _deliver(srv, _sent_raw(), monkeypatch)
    with index_db.connect() as c:                       # Zustand wie 0.2.0: kein Kennzeichen
        c.execute("DELETE FROM sent_local")
    _sync(srv)
    assert len([m for m in _visible() if m["subject"] == "Test"]) == 1
    assert [m for m in _only_archive() if m["subject"] == "Test"] == []
