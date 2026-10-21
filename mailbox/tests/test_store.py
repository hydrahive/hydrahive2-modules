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
    assert r["subject"] == "Termin morgen" and r["uid"] == 1 and r["seen"] == 1 and r["folder_id"] == fid
    assert r["date"] == "2026-10-20T07:15:00Z" and r["path"] == "x/plain.eml" and r["deleted_on_server"] == 0


def test_gleiche_mail_zweimal_ein_eintrag(archive):
    _, a = _add(archive)
    _, b = _add(archive)
    assert a == b


def test_gleiche_mail_anderer_ordner_zieht_um(archive):
    """Auf dem Server verschoben: derselbe Eintrag, neuer Ordner und neue UID."""
    from backend import index_db
    _, a = _add(archive, folder="INBOX", uid=5)
    fid2, b = _add(archive, folder="Ablage", uid=9)
    with index_db.connect() as c:
        r = c.execute("SELECT folder_id, uid FROM messages WHERE id=?", (a,)).fetchone()
    assert a == b and (r["folder_id"], r["uid"]) == (fid2, 9)


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
    assert store.mark_gone(fid, keep_uids={8}) == 1
    with index_db.connect() as c:
        r = c.execute("SELECT deleted_on_server, uid FROM messages WHERE id=?", (mid,)).fetchone()
        n = c.execute("SELECT count(*) FROM messages").fetchone()[0]
    assert tuple(r) == (1, None) and n == 2


def test_wieder_da_nach_loeschung(archive):
    """Kam dieselbe Mail später wieder (z. B. aus dem Papierkorb zurück), ist sie nicht mehr als gelöscht markiert."""
    from backend import index_db, store
    fid, mid = _add(archive, uid=7)
    store.mark_gone(fid, keep_uids=set())
    _add(archive, uid=11)
    with index_db.connect() as c:
        assert tuple(c.execute("SELECT deleted_on_server, uid FROM messages WHERE id=?", (mid,)).fetchone()) == (0, 11)


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
    store.mark_gone(fid, keep_uids={1})          # die ungelesene ist auf dem Server weg
    store.recount(fid)
    with index_db.connect() as c:
        assert tuple(c.execute("SELECT total, unread FROM folders WHERE id=?", (fid,)).fetchone()) == (1, 0)


def test_unterhaltung_gemeinsamer_schluessel(archive):
    from backend import threads
    assert threads.key("<root@x>", "Re: Termin", "<m2@x>") == "<root@x>"
    assert threads.key("", "AW: WG: Fwd: Re:  Termin  morgen", "") == "subj:termin morgen"
    assert threads.key("", "", "<m3@x>") == "<m3@x>"
