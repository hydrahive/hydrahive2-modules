"""M1 Schritt 6: Index – Ordner, Nachrichten (Upsert über Hash), Flags, Server-Löschung, Volltext, Unterhaltungen."""
from __future__ import annotations

from conftest import eml

ACC = "acc1"


def _add(archive, name="plain", folder="INBOX", uid=1, flags=()):
    from backend import parse, store
    raw = eml(name)
    fid = store.folder(ACC, folder, role="inbox" if folder == "INBOX" else "")
    return fid, store.add_message(ACC, fid, uid, parse.parse(raw), path=f"x/{name}.eml", size=len(raw), flags=set(flags))


def test_ordner_einmal(archive):
    from backend import store
    a = store.folder(ACC, "INBOX", role="inbox")
    assert store.folder(ACC, "INBOX", role="inbox") == a
    assert store.folder("acc2", "INBOX", role="inbox") != a


def test_nachricht_und_felder(archive):
    from backend import index_db
    fid, mid = _add(archive, flags={"\\Seen"})
    with index_db.connect() as c:
        r = c.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone()
        loc = c.execute("SELECT folder_id, uid FROM locations WHERE message_id=?", (mid,)).fetchall()
    assert r["subject"] == "Termin morgen" and r["seen"] == 1 and r["folder_id"] == fid
    assert [tuple(x) for x in loc] == [(fid, 1)]
    assert r["date"] == "2026-10-20T07:15:00Z" and r["path"] == "x/plain.eml" and r["deleted_on_server"] == 0


def test_gleiche_mail_zweimal_ein_eintrag(archive):
    _, a = _add(archive)
    _, b = _add(archive)
    assert a == b


def test_gleiche_mail_zweiter_ordner_zweiter_fundort(archive):
    """Gmail-Labels: dieselbe Mail in INBOX und „Alle Nachrichten“ → ein Eintrag, zwei Fundorte, Ordner bleibt INBOX."""
    from backend import index_db
    fid1, a = _add(archive, folder="INBOX", uid=5)
    fid2, b = _add(archive, folder="Alle", uid=9)
    with index_db.connect() as c:
        r = c.execute("SELECT folder_id FROM messages WHERE id=?", (a,)).fetchone()
        locs = sorted(tuple(x) for x in c.execute("SELECT folder_id, uid FROM locations WHERE message_id=?", (a,)))
    assert a == b and r["folder_id"] == fid1 and locs == sorted([(fid1, 5), (fid2, 9)])


def test_verschoben_zieht_hauptordner_um(archive):
    """Auf dem Server verschoben (alter Fundort weg, neuer da): reconcile meldet den Umzug, gelöscht wird nichts."""
    from backend import store
    fid1, a = _add(archive, folder="INBOX", uid=5)
    fid2, _ = _add(archive, folder="Ablage", uid=9)
    store.drop_locations(fid1, keep_uids=set())
    r = store.reconcile("acc1")
    assert r["gone"] == 0 and r["moves"] == [(a, "x/plain.eml", fid2)]
    store.set_primary(a, fid2, "y/plain.eml")
    assert store.reconcile("acc1")["moves"] == []


def test_flags_abgleich(archive):
    from backend import index_db, store
    fid, mid = _add(archive, uid=3)
    store.set_flags(fid, {3: {"\\Seen", "\\Flagged"}})
    with index_db.connect() as c:
        r = c.execute("SELECT seen, flagged, answered FROM messages WHERE id=?", (mid,)).fetchone()
    assert tuple(r) == (1, 1, 0)
    store.set_flags(fid, {3: set()})
    with index_db.connect() as c:
        assert tuple(c.execute("SELECT seen, flagged FROM messages WHERE id=?", (mid,)).fetchone()) == (0, 0)


def test_server_loeschung_markiert_eintrag_bleibt(archive):
    from backend import index_db, store
    fid, mid = _add(archive, uid=7)
    _add(archive, name="latin1", uid=8)
    assert store.drop_locations(fid, keep_uids={8}) == 1
    assert store.reconcile("acc1")["gone"] == 1
    with index_db.connect() as c:
        r = c.execute("SELECT deleted_on_server, folder_id FROM messages WHERE id=?", (mid,)).fetchone()
        n = c.execute("SELECT count(*) FROM messages").fetchone()[0]
    assert tuple(r) == (1, fid) and n == 2, "bleibt im Index, letzter Ordner bleibt stehen"
    assert store.reconcile("acc1")["gone"] == 0, "nur neu Verschwundene zählen"


def test_wieder_da_nach_loeschung(archive):
    """Kam dieselbe Mail später wieder (z. B. aus dem Papierkorb zurück), ist sie nicht mehr als gelöscht markiert."""
    from backend import index_db, store
    fid, mid = _add(archive, uid=7)
    store.drop_locations(fid, keep_uids=set())
    store.reconcile("acc1")
    _add(archive, uid=11)
    with index_db.connect() as c:
        assert c.execute("SELECT deleted_on_server FROM messages WHERE id=?", (mid,)).fetchone()[0] == 0
    assert store.known_uids(fid) == {11}


def test_finden_ueber_kopf(archive):
    """Neue UID, aber Message-ID + Größe bekannt → ohne Inhalt laden zuordnen."""
    from backend import store
    _, mid = _add(archive)
    assert store.find_header("acc1", "<plain-1@example.org>", len(eml("plain")))["id"] == mid
    assert store.find_header("acc1", "<plain-1@example.org>", 5) is None, "Größe muss passen"
    assert store.find_header("acc1", "", len(eml("plain"))) is None, "ohne Message-ID nie raten"
    assert store.find_header("acc2", "<plain-1@example.org>", len(eml("plain"))) is None


def test_bekannte_uids(archive):
    from backend import store
    fid, _ = _add(archive, uid=4)
    _add(archive, name="latin1", uid=9)
    assert store.known_uids(fid) == {4, 9}


def test_volltext_eintrag(archive):
    from backend import index_db
    _add(archive)
    with index_db.connect() as c:
        hits = c.execute("SELECT rowid FROM messages_fts WHERE messages_fts MATCH 'termin'").fetchall()
    assert len(hits) == 1


def test_volltext_umlaute_ohne_akzent(archive):
    from backend import index_db
    _add(archive, name="latin1")
    with index_db.connect() as c:
        assert c.execute("SELECT count(*) FROM messages_fts WHERE messages_fts MATCH 'koln'").fetchone()[0] == 1


def test_ordner_zaehler(archive):
    from backend import index_db, store
    fid, _ = _add(archive, uid=1, flags={"\\Seen"})
    _add(archive, name="latin1", uid=2)
    store.recount(fid)
    with index_db.connect() as c:
        assert tuple(c.execute("SELECT total, unread FROM folders WHERE id=?", (fid,)).fetchone()) == (2, 1)
    store.drop_locations(fid, keep_uids={1})     # die ungelesene ist auf dem Server weg
    store.reconcile("acc1")
    store.recount(fid)
    with index_db.connect() as c:
        assert tuple(c.execute("SELECT total, unread FROM folders WHERE id=?", (fid,)).fetchone()) == (1, 0)


def test_unterhaltung_gemeinsamer_schluessel(archive):
    from backend import threads
    assert threads.key("<root@x>", "Re: Termin", "<m2@x>") == "<root@x>"
    assert threads.key("", "AW: WG: Fwd: Re:  Termin  morgen", "") == "subj:termin morgen"
    assert threads.key("", "", "<m3@x>") == "<m3@x>"
