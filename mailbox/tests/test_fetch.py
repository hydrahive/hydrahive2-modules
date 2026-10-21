"""M1 Schritt 7: Abgleich gegen Fake-IMAP – alle Ordner, nur Neues, UIDVALIDITY, Server-Löschung, Flags, Abbruch."""
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer
from conftest import eml

ACC = {"id": "acc1", "address": "till@example.net"}


def _mail(n: int, subject="Mail") -> bytes:
    return (f"From: a{n}@example.org\r\nSubject: {subject} {n}\r\nMessage-ID: <m{n}@example.org>\r\n"
            f"Date: Tue, 20 Oct 2026 09:{n % 60:02d}:00 +0000\r\n\r\nText {n}\r\n").encode()


@pytest.fixture
def server():
    s = FakeServer()
    s.box("Gesendet", special="\\Sent")
    s.box("Archiv/2019")
    s.box("Gelöschte Elemente", special="\\Trash")
    return s


def _sync(server, batch=200):
    from backend import fetch
    return fetch.sync_account(ACC, FakeIMAP(server), batch=batch)


def _count(where="1=1", args=()):
    from backend import index_db
    with index_db.connect() as c:
        return c.execute(f"SELECT count(*) FROM messages WHERE {where}", args).fetchone()[0]


def test_alle_ordner_alle_mails(archive, server):
    for n in range(5):
        server.boxes["INBOX"].add(_mail(n))
    server.boxes["Gesendet"].add(_mail(10))
    server.boxes["Archiv/2019"].add(_mail(11))
    server.boxes["Gelöschte Elemente"].add(eml("latin1"))
    r = _sync(server)
    assert r["new"] == 8 and _count() == 8
    assert len(list(archive.rglob("*.eml"))) == 8
    assert (archive / "till@example.net" / "Gel_schte_Elemente").exists() or \
        (archive / "till@example.net" / "Gelöschte_Elemente").exists()


def test_rollen_aus_special_use(archive, server):
    from backend import index_db
    _sync(server)
    with index_db.connect() as c:
        roles = dict(c.execute("SELECT name, role FROM folders").fetchall())
    assert roles["INBOX"] == "inbox" and roles["Gesendet"] == "sent" and roles["Gelöschte Elemente"] == "trash"


def test_zweiter_lauf_holt_nur_neues(archive, server):
    for n in range(3):
        server.boxes["INBOX"].add(_mail(n))
    _sync(server)
    before = server.fetches
    server.boxes["INBOX"].add(_mail(99))
    r = _sync(server)
    assert r["new"] == 1 and _count() == 4
    assert server.fetches - before <= 2 * len(server.boxes), "nur Flags + ein Paket Neues je Ordner"


def test_pakete(archive, server):
    for n in range(25):
        server.boxes["INBOX"].add(_mail(n))
    r = _sync(server, batch=10)
    assert r["new"] == 25 and _count() == 25


def test_server_loeschung_bleibt_im_archiv(archive, server):
    uids = [server.boxes["INBOX"].add(_mail(n)) for n in range(3)]
    _sync(server)
    del server.boxes["INBOX"].msgs[uids[1]]
    r = _sync(server)
    assert r["gone"] == 1 and _count("deleted_on_server=1") == 1 and _count() == 3
    assert len(list(archive.rglob("*.eml"))) == 3


def test_flags_kommen_an(archive, server):
    uid = server.boxes["INBOX"].add(_mail(1))
    _sync(server)
    assert _count("seen=1") == 0
    server.boxes["INBOX"].msgs[uid][1].add("\\Seen")
    _sync(server)
    assert _count("seen=1") == 1


def test_uidvalidity_wechsel_ohne_doppelte(archive, server):
    for n in range(3):
        server.boxes["INBOX"].add(_mail(n))
    _sync(server)
    box = server.boxes["INBOX"]
    old = dict(box.msgs)
    box.msgs.clear()
    box.uidvalidity, box.next_uid = 2000, 50
    for raw, fl in old.values():
        box.add(raw, fl)
    r = _sync(server)
    assert _count() == 3 and _count("deleted_on_server=1") == 0 and r["new"] == 0
    from backend import index_db
    with index_db.connect() as c:
        assert sorted(x[0] for x in c.execute("SELECT uid FROM locations")) == [50, 51, 52]


def test_verschoben_auf_dem_server(archive, server):
    uid = server.boxes["INBOX"].add(_mail(7))
    _sync(server)
    raw, fl = server.boxes["INBOX"].msgs.pop(uid)
    server.boxes["Archiv/2019"].add(raw, fl)
    _sync(server)
    assert _count() == 1 and _count("deleted_on_server=1") == 0
    files = list(archive.rglob("*.eml"))
    assert len(files) == 1 and "Archiv/2019" in str(files[0])


def test_abbruch_mitten_im_paket_macht_spaeter_weiter(archive, server):
    from backend import fetch
    for n in range(30):
        server.boxes["INBOX"].add(_mail(n))
    server.fail_fetch_after = 2
    with pytest.raises(fetch.SyncError):
        _sync(server, batch=10)
    done = _count()
    assert 0 < done < 30
    server.fail_fetch_after, server.fetches = None, 0
    _sync(server, batch=10)
    assert _count() == 30 and len(list(archive.rglob("*.eml"))) == 30


def test_falsches_passwort(archive, server):
    from backend import fetch
    server.password = "anders"
    with pytest.raises(fetch.AuthFailed):
        fetch.sync_account(ACC, FakeIMAP(server), login=("till@example.net", "pw"))


def test_ordner_auf_server_weg_inhalt_bleibt(archive, server):
    server.boxes["Archiv/2019"].add(_mail(5))
    _sync(server)
    del server.boxes["Archiv/2019"]
    _sync(server)
    from backend import index_db
    with index_db.connect() as c:
        assert c.execute("SELECT gone FROM folders WHERE name='Archiv/2019'").fetchone()[0] == 1
    assert _count("deleted_on_server=1") == 1 and len(list(archive.rglob("*.eml"))) == 1


def test_manifest_waechst_mit(archive, server):
    for n in range(4):
        server.boxes["INBOX"].add(_mail(n))
    _sync(server)
    lines = [x for x in (archive / "till@example.net" / "MANIFEST.tsv").read_text().splitlines() if not x.startswith("#")]
    assert len(lines) == 4


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
        fetch.sync_account(ACC, FakeIMAP(server), login=("till@example.net", "pw"))
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
