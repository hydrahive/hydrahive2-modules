"""0.3.0 Gesendet-Verknüpfung (Teil 2): Grenzfälle – Kennzeichen beim Senden, nur Gesendet-Ordner zählt, Rückkehr,
Altlast-Erkennung eng (nichts anderes wird zurückgestellt)."""
from __future__ import annotations

from test_sent_merge import ACC_S, _deliver, _only_archive, _rewritten, _sent_raw, _srv, _sync, _visible


def _sl():
    from backend import index_db
    with index_db.connect() as c:
        return {r[0]: r[1] for r in c.execute("SELECT message_id, superseded FROM sent_local")}


def test_senden_kennzeichnet_eigene_kopie(archive, monkeypatch):
    from backend import index_db
    srv = _srv()
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch)
    with index_db.connect() as c:
        mid = c.execute("SELECT id FROM messages WHERE message_id=?", (built.message_id,)).fetchone()[0]
    assert _sl() == {mid: 0}


def test_fassung_in_anderem_ordner_stellt_nicht_zurueck(archive, monkeypatch):
    """Server-Fassung landet NICHT im Gesendet-Ordner (z. B. Regel verschiebt sie ins Archiv) → eigene Kopie bleibt
    sichtbar; zurückgestellt wird nur gegen eine Fassung im Gesendet-Ordner."""
    srv = _srv()
    srv.box("Archiv")
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch, rewrite=False)
    srv.boxes["Sent"].msgs.clear()
    srv.boxes["Archiv"].add(_rewritten(built.raw))
    _sync(srv)
    assert list(_sl().values()) == [0]
    assert len([m for m in _visible() if m["subject"] == "Test"]) == 2


def test_rueckkehr_wenn_fassung_verschwindet_aus_index(archive, monkeypatch):
    """superseded ist kein Einbahnweg: gibt es keine Server-Fassung mehr im Index, wird die eigene Kopie wieder gezeigt."""
    from backend import index_db, sent_link
    srv = _srv()
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch)
    _sync(srv)
    assert list(_sl().values()) == [1]
    with index_db.connect() as c:                      # Server-Fassung aus dem Index (Neuaufbau o. Ä.)
        other = c.execute("SELECT id FROM messages WHERE message_id=? AND id NOT IN (SELECT message_id FROM sent_local)",
                          (built.message_id,)).fetchone()[0]
        c.execute("DELETE FROM locations WHERE message_id=?", (other,))
        c.execute("UPDATE messages SET message_id='' WHERE id=?", (other,))
    sent_link.refresh(ACC_S["id"])
    assert list(_sl().values()) == [0]


def test_altlast_nur_eigene_gesendete_kopien(archive, monkeypatch):
    """Altlast-Erkennung greift nur bei: nur im Archiv, Hauptordner Gesendet, Server-Fassung mit gleicher Message-ID.
    Eine empfangene, auf dem Server gelöschte Posteingangs-Mail mit gleicher Message-ID bleibt unter „Nur im Archiv“."""
    from backend import index_db
    srv = _srv()
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch)
    srv.boxes["INBOX"].add(b"From: x@y.de\r\nSubject: Echo\r\nMessage-ID: " + built.message_id.encode() + b"\r\n\r\nx")
    _sync(srv)
    srv.boxes["INBOX"].msgs.clear()
    with index_db.connect() as c:
        c.execute("DELETE FROM sent_local WHERE message_id IN (SELECT id FROM messages WHERE account_id=?)", (ACC_S["id"],))
    _sync(srv)
    assert [m["subject"] for m in _only_archive()] == ["Echo"]
    assert len(_sl()) == 1


def test_altlast_nicht_wenn_kopie_noch_auf_dem_server(archive, monkeypatch):
    """Ohne Umschreiben ist die eigene Kopie selbst die Server-Fassung (Fundort) – keine Altlast, nichts zurückstellen."""
    from backend import index_db
    srv = _srv()
    _sync(srv)
    _deliver(srv, _sent_raw(), monkeypatch, rewrite=False)
    with index_db.connect() as c:
        c.execute("DELETE FROM sent_local WHERE message_id IN (SELECT id FROM messages WHERE account_id=?)", (ACC_S["id"],))
    _sync(srv)
    assert _sl() == {} and len([m for m in _visible() if m["subject"] == "Test"]) == 1


def test_gesendete_mail_sofort_loeschbar_ohne_abgleich(archive, monkeypatch):
    """Befund Browser-Test 22.10.: Direkt nach dem Senden (vor dem nächsten Abgleich) hatte die eigene Kopie keinen
    Fundort → Löschen meldete „übersprungen“. Mit APPENDUID (UIDPLUS) ist der Fundort sofort bekannt."""
    from _fake_imap_write import FakeIMAPW
    from backend import actions, index_db
    srv = _srv()
    srv.box("Trash", special="\\Trash")
    _sync(srv)
    built = _sent_raw()
    _deliver(srv, built, monkeypatch, rewrite=False)
    with index_db.connect() as c:
        mid = c.execute("SELECT id FROM messages WHERE message_id=?", (built.message_id,)).fetchone()[0]
    r = actions.apply(ACC_S, FakeIMAPW(srv, caps=("MOVE", "UIDPLUS", "UNSELECT")), "delete", [mid])
    assert r == {"done": 1, "skipped": 0}
    assert srv.boxes["Sent"].msgs == {} and len(srv.boxes["Trash"].msgs) == 1


def test_ohne_appenduid_bleibt_es_beim_abgleich(archive, monkeypatch):
    """Server ohne UIDPLUS (keine APPENDUID-Antwort): kein geratener Fundort; der Abgleich trägt ihn nach."""
    from _fake_imap import FakeIMAP
    from backend import index_db, outbox, smtp_send
    srv = _srv()
    _sync(srv)
    monkeypatch.setattr(smtp_send, "send", lambda *a, **kw: {})

    class NoUidplus(FakeIMAP):
        def append(self, mailbox, flags, dt, message):
            typ, _ = super().append(mailbox, flags, dt, message)
            return typ, [b"APPEND completed"]
    built = _sent_raw()
    outbox.deliver(ACC_S, "pw", built, open_imap=lambda a: NoUidplus(srv))
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM locations l JOIN messages m ON m.id=l.message_id WHERE m.message_id=?",
                         (built.message_id,)).fetchone()[0] == 0
    _sync(srv)
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM locations l JOIN messages m ON m.id=l.message_id WHERE m.message_id=?",
                         (built.message_id,)).fetchone()[0] == 1


def test_appenduid_mit_falscher_uidvalidity_ignoriert(archive, monkeypatch):
    """APPENDUID nennt eine andere UIDVALIDITY als der Index kennt → Fundort nicht eintragen (UID gehört zu einer
    anderen Zählung)."""
    from _fake_imap import FakeIMAP
    from backend import index_db, outbox, smtp_send
    srv = _srv()
    _sync(srv)
    monkeypatch.setattr(smtp_send, "send", lambda *a, **kw: {})

    class Fremd(FakeIMAP):
        def append(self, mailbox, flags, dt, message):
            typ, _ = super().append(mailbox, flags, dt, message)
            return typ, [b"[APPENDUID 999999 1] APPEND completed"]
    built = _sent_raw()
    outbox.deliver(ACC_S, "pw", built, open_imap=lambda a: Fremd(srv))
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM locations").fetchone()[0] == 0
