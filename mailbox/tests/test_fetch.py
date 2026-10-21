"""M1 Schritt 7: Abgleich gegen Fake-IMAP – alle Ordner, nur Neues, UIDVALIDITY, Server-Löschung, Flags, Abbruch."""
# ruff: noqa: F811 - pytest-Fixtures aus _fetch_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from _fake_imap import FakeIMAP, FakeServer  # noqa: F401
from conftest import eml  # noqa: F401
from _fetch_base import ACC, _count, _mail, _sync, server  # noqa: F401 - Fixtures/Hilfen


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


