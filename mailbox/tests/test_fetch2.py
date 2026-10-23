"""M1 Schritt 7, Teil 2: Abgleich – kein Doppelt-Laden, Gmail-Labels, UTF-7-Ordner, nur lesend."""
# ruff: noqa: F811 - pytest-Fixtures aus _fetch_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer  # noqa: F401
from _fetch_base import ACC, _count, _mail, _sync, server  # noqa: F401 - Fixtures/Hilfen


def test_uidvalidity_wechsel_laedt_inhalte_nicht_neu(archive, server):
    """Erkannt über Message-ID + Größe: kein zweites Herunterladen der Inhalte (große Postfächer!)."""
    from backend import fetch
    for n in range(3):
        server.boxes["INBOX"].add(_mail(n))
    _sync(server)
    box = server.boxes["INBOX"]
    old = list(box.msgs.values())
    box.msgs.clear()
    box.uidvalidity, box.next_uid = 2000, 50
    for raw, fl in old:
        box.add(raw, fl)
    calls = []
    real = fetch._bodies
    fetch._bodies = lambda conn, uids: (calls.append(list(uids)), real(conn, uids))[1]
    try:
        _sync(server)
    finally:
        fetch._bodies = real
    assert calls == [], "keine Inhalte erneut geladen"


def test_gleiche_mail_in_zwei_ordnern_eine_datei(archive, server):
    """Gmail: Posteingang + „Alle Nachrichten“ – eine Archivdatei, zwei Fundorte."""
    server.box("[Gmail]/Alle Nachrichten", special="\\All")
    raw = _mail(3)
    server.boxes["INBOX"].add(raw)
    server.boxes["[Gmail]/Alle Nachrichten"].add(raw)
    _sync(server)
    assert _count() == 1 and len(list(archive.rglob("*.eml"))) == 1
    from backend import index_db
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM locations").fetchone()[0] == 2


def test_umlaut_ordner_utf7(archive, server):
    server.box("Entwürfe", special="\\Drafts").add(_mail(1))
    _sync(server)
    from backend import index_db
    with index_db.connect() as c:
        assert c.execute("SELECT role FROM folders WHERE name='Entwürfe'").fetchone()[0] == "drafts"
    assert _count() == 1


def test_noselect_wird_uebersprungen():
    from backend import imap_conn
    out = imap_conn.parse_list([b'(\\HasNoChildren) "/" "INBOX"', b'(\\Noselect \\HasChildren) "/" "[Gmail]"',
                                b'(\\HasNoChildren \\Sent) "/" "Sent Items"', b'(\\HasNoChildren) "." Archiv.2020',
                                b"kaputt", None])
    assert [(f["name"], f["role"]) for f in out] == [("INBOX", "inbox"), ("Sent Items", "sent"), ("Archiv.2020", "")]


def test_utf7_rundum():
    from backend import imap_conn
    for name in ("Entwürfe", "Gelöschte Elemente", "A&B", "日本", "Ordner \"x\""):
        assert imap_conn.utf7_decode(imap_conn.utf7_encode(name)) == name
    assert imap_conn.utf7_encode("Entwürfe") == "Entw&APw-rfe"
    assert imap_conn.quote('a"b') == '"a\\"b"'


def test_falsches_passwort_markiert_nichts(archive, server):
    from backend import fetch
    server.boxes["INBOX"].add(_mail(1))
    server.password = "anders"
    with pytest.raises(fetch.AuthFailed):
        fetch.sync_account(ACC, FakeIMAP(server), login=lambda c: c.login("till@example.net", "pw"))
    assert _count() == 0


def test_abgleich_nur_lesend_und_ohne_doppelt_laden(archive, server):
    """Ordner nur read-only öffnen (kein \\Recent/Gelesen ändern); Bekanntes nie ein zweites Mal herunterladen."""
    for n in range(4):
        server.boxes["INBOX"].add(_mail(n))
    _sync(server)
    assert server.body_fetches == 4 and server.writable_selects == 0
    _sync(server)
    assert server.body_fetches == 4, "zweiter Lauf lädt keine Inhalte"


def test_ordnername_mit_kaufmanns_und(archive, server):
    server.box("A&B Rechnungen").add(_mail(2))
    _sync(server)
    assert _count() == 1


def test_mails_ohne_message_id_nicht_doppelt_geladen(archive, server):
    """Ohne Message-ID greift die Kopf-Erkennung nicht – bekannte UIDs müssen trotzdem übersprungen werden."""
    for n in range(3):
        server.boxes["INBOX"].add(f"From: x@y.de\r\nSubject: ohne id {n}\r\n\r\nText {n}\r\n".encode())
    _sync(server)
    _sync(server)
    assert server.body_fetches == 3 and _count() == 3


def test_posteingang_zuerst_und_alle_ordner_sofort_sichtbar(archive):
    """Yahoo listet „Archive“ vor INBOX: trotzdem erst den Posteingang laden; alle Ordner stehen vor dem ersten Laden fest."""
    from backend import fetch, index_db
    s = FakeServer()
    s.boxes = {"Archive": s.boxes.get("Archive") or __import__("_fake_imap").Box("Archive"), "INBOX": s.boxes["INBOX"]}
    s.box("Sent", special="\\Sent")
    s.boxes["Archive"].add(_mail(1))
    s.boxes["INBOX"].add(_mail(2))
    seen = []
    real = fetch._bodies

    def spy(conn, uids):
        with index_db.connect() as c:
            seen.append((conn.selected.name, c.execute("SELECT count(*) FROM folders").fetchone()[0]))
        return real(conn, uids)
    fetch._bodies = spy
    try:
        fetch.sync_account(ACC, FakeIMAP(s))
    finally:
        fetch._bodies = real
    assert seen[0] == ("INBOX", 3), seen


def test_fortschritt_je_paket_mit_zaehlern(archive, server):
    """Nach jedem Paket: Rückmeldung + Ordnerzähler aktuell (sonst sieht man stundenlang „0“)."""
    from backend import fetch, index_db
    for n in range(25):
        server.boxes["INBOX"].add(_mail(n))
    calls = []

    def cb(c):
        with index_db.connect() as db:
            total = db.execute("SELECT total FROM folders WHERE name='INBOX'").fetchone()[0]
        calls.append((c["new"], c["folders_total"], total))
    fetch.sync_account(ACC, FakeIMAP(server), batch=10, on_progress=cb)
    inbox = [x for x in calls if x[2] > 0]
    assert inbox[:3] == [(10, 4, 10), (20, 4, 20), (25, 4, 25)], calls
