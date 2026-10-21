"""M2 Schritt 7: Aktionen auf dem Server – gelesen/markiert, verschieben, löschen. Das Archiv bleibt immer.

Sicherheit: Vor jeder Änderung wird die UID über die Message-ID im Ordner bestätigt (UIDVALIDITY/fremde Programme).
Endgültig entfernt wird nur gezielt (UID EXPUNGE, UIDPLUS) – nie ein pauschales EXPUNGE, das fremde \\Deleted-Mails
mitnehmen würde.
"""
from __future__ import annotations

import pytest
from _fake_imap import FakeServer
from _fake_imap_write import FakeIMAPW
from _fetch_base import ACC, _mail

CAPS_ALL = ("MOVE", "UIDPLUS", "UNSELECT")


@pytest.fixture
def srv():
    s = FakeServer()
    s.box("Papierkorb", special="\\Trash")
    s.box("Projekte")
    for n in range(3):
        s.boxes["INBOX"].add(_mail(n))
    return s


def _sync(srv):
    from backend import fetch
    from _fake_imap import FakeIMAP
    fetch.sync_account(ACC, FakeIMAP(srv))


def _mid(n: int) -> int:
    from backend import index_db
    with index_db.connect() as c:
        return c.execute("SELECT id FROM messages WHERE message_id=?", (f"<m{n}@example.org>",)).fetchone()[0]


def _row(mid):
    from backend import index_db
    with index_db.connect() as c:
        r = c.execute("SELECT m.*, f.name AS folder FROM messages m JOIN folders f ON f.id=m.folder_id WHERE m.id=?",
                      (mid,)).fetchone()
        locs = [tuple(x) for x in c.execute("SELECT f.name, l.uid FROM locations l JOIN folders f ON f.id=l.folder_id "
                                            "WHERE l.message_id=? ORDER BY f.name", (mid,))]
    return dict(r), locs


def _run(srv, action, mid, caps=CAPS_ALL, **kw):
    from backend import actions
    conn = FakeIMAPW(srv, caps=caps)
    return actions.apply(ACC, conn, action, [mid], **kw), conn


def _subjects(box):
    return sorted(raw.split(b"Subject: ")[1].split(b"\r\n")[0].decode() for raw, _ in box.msgs.values())


@pytest.mark.parametrize("action, flag, on", [("seen", "\\Seen", True), ("unseen", "\\Seen", False),
                                              ("flag", "\\Flagged", True), ("unflag", "\\Flagged", False)])
def test_flags(archive, srv, action, flag, on):
    if not on:
        srv.boxes["INBOX"].msgs[1][1].add(flag)
    _sync(srv)
    r, conn = _run(srv, action, _mid(0))
    assert r == {"done": 1, "skipped": 0}
    assert (flag in srv.boxes["INBOX"].msgs[1][1]) is on
    col = "seen" if flag == "\\Seen" else "flagged"
    assert _row(_mid(0))[0][col] == int(on), "Index sofort aktuell, nicht erst nach dem nächsten Abgleich"
    assert srv.writes_readonly == 0


@pytest.mark.parametrize("caps", [CAPS_ALL, ("UIDPLUS",)])
def test_verschieben(archive, srv, caps):
    _sync(srv)
    r, _ = _run(srv, "move", _mid(1), caps=caps, target="Projekte")
    assert r["done"] == 1 and _subjects(srv.boxes["INBOX"]) == ["Mail 0", "Mail 2"]
    assert _subjects(srv.boxes["Projekte"]) == ["Mail 1"]
    assert srv.full_expunges == 0
    _sync(srv)
    row, locs = _row(_mid(1))
    assert [n for n, _ in locs] == ["Projekte"] and row["deleted_on_server"] == 0


def test_verschieben_ohne_move_ohne_uidplus_kein_pauschales_expunge(archive, srv):
    """Ohne MOVE und ohne UIDPLUS: kopieren + \\Deleted setzen, aber NIE pauschal EXPUNGE (würde fremde
    \\Deleted-Mails mitnehmen). Die Mail bleibt als gelöscht markiert, bis das Mailprogramm aufräumt."""
    srv.boxes["INBOX"].msgs[3][1].add("\\Deleted")          # fremde, von anderem Programm markierte Mail
    _sync(srv)
    r, _ = _run(srv, "move", _mid(1), caps=(), target="Projekte")
    assert r["done"] == 1 and srv.full_expunges == 0
    assert _subjects(srv.boxes["Projekte"]) == ["Mail 1"]
    assert "\\Deleted" in srv.boxes["INBOX"].msgs[2][1] and 3 in srv.boxes["INBOX"].msgs, "fremde Mail unberührt"


def test_loeschen_in_den_papierkorb_archiv_bleibt(archive, srv):
    from backend import archive as arch
    _sync(srv)
    mid = _mid(0)
    path = _row(mid)[0]["path"]
    r, _ = _run(srv, "delete", mid)
    assert r["done"] == 1 and _subjects(srv.boxes["Papierkorb"]) == ["Mail 0"]
    assert arch.read(path).startswith(b"From: a0@")
    _sync(srv)
    assert _row(mid)[1] == [("Papierkorb", 1)]


def test_loeschen_im_papierkorb_entfernt_nur_auf_dem_server(archive, srv):
    """Endgültig löschen (aus dem Papierkorb): Server weg, Archiv bleibt, Mail erscheint als „nur im Archiv“."""
    from backend import archive as arch
    srv.boxes["Papierkorb"].add(_mail(9))
    _sync(srv)
    mid = _mid(9)
    path = _row(mid)[0]["path"]
    r, _ = _run(srv, "delete", mid)
    assert r["done"] == 1 and srv.boxes["Papierkorb"].msgs == {} and srv.full_expunges == 0
    _sync(srv)
    row, locs = _row(mid)
    assert locs == [] and row["deleted_on_server"] == 1 and arch.read(path).startswith(b"From: a9@")


def test_loeschen_ohne_papierkorb_ordner(archive):
    s = FakeServer()
    s.boxes["INBOX"].add(_mail(0))
    _sync(s)
    r, _ = _run(s, "delete", _mid(0))
    assert r["done"] == 1 and s.boxes["INBOX"].msgs == {} and s.full_expunges == 0


def test_endgueltig_ohne_uidplus_nur_markiert(archive, srv):
    srv.boxes["Papierkorb"].add(_mail(9))
    _sync(srv)
    r, _ = _run(srv, "delete", _mid(9), caps=("MOVE",))
    assert r["done"] == 1 and "\\Deleted" in srv.boxes["Papierkorb"].msgs[1][1] and srv.full_expunges == 0


def test_uid_zeigt_auf_andere_mail_nichts_anfassen(archive, srv):
    """Ein anderes Programm hat umsortiert: UID 2 ist jetzt eine andere Mail → überspringen, nichts verändern."""
    _sync(srv)
    box = srv.boxes["INBOX"]
    box.msgs[2] = (_mail(7), set())                          # gleiche UID, andere Mail (ohne UIDVALIDITY-Wechsel)
    r, _ = _run(srv, "delete", _mid(1))
    assert r == {"done": 0, "skipped": 1} and 2 in box.msgs and srv.boxes["Papierkorb"].msgs == {}


def test_nur_im_archiv_wird_uebersprungen(archive, srv):
    _sync(srv)
    srv.boxes["INBOX"].msgs.pop(1)
    _sync(srv)
    r, _ = _run(srv, "delete", _mid(0))
    assert r == {"done": 0, "skipped": 1}


def test_ziel_eines_anderen_kontos_abgelehnt(archive, srv):
    from backend import actions, store
    _sync(srv)
    store.folder("fremd", "Geheim")
    with pytest.raises(actions.ActionError):
        _run(srv, "move", _mid(0), target="Geheim-gibts-nicht")
    with pytest.raises(actions.ActionError):
        _run(srv, "move", _mid(0), target="")


def test_unbekannte_aktion(archive, srv):
    from backend import actions
    _sync(srv)
    with pytest.raises(actions.ActionError):
        _run(srv, "expunge_all", _mid(0))


def test_mehrere_auf_einmal(archive, srv):
    from backend import actions
    _sync(srv)
    r = actions.apply(ACC, FakeIMAPW(srv), "seen", [_mid(0), _mid(1), _mid(2)])
    assert r == {"done": 3, "skipped": 0}
    assert all("\\Seen" in fl for _, fl in srv.boxes["INBOX"].msgs.values())


def test_ziel_nur_aus_eigenen_ordnern(archive, srv):
    """Ziel muss ein bekannter Ordner DIESES Kontos sein – ein gleichnamiger Ordner eines anderen Kontos zählt nicht."""
    from backend import actions, store
    _sync(srv)
    store.folder("fremd", "Nur-Fremd")
    srv.box("Nur-Fremd")
    with pytest.raises(actions.ActionError):
        _run(srv, "move", _mid(0), target="Nur-Fremd")
    assert srv.boxes["Nur-Fremd"].msgs == {}


def test_ordner_auf_dem_server_weg_wird_uebersprungen(archive, srv):
    _sync(srv)
    del srv.boxes["INBOX"]
    srv.boxes["INBOX "] = srv.box("Platzhalter")       # Server ohne den Ordner
    r, _ = _run(srv, "seen", _mid(0))
    assert r == {"done": 0, "skipped": 1}


@pytest.mark.parametrize("mid", ['<a@b" OR ALL "x>', "<a b@c>", "", "kein-spitz@x", '<a\\"@b>'])
def test_boese_message_id_wird_nicht_in_den_befehl_gebaut(archive, mid):
    """Message-ID kommt aus fremden Mails → nur unverdächtige Werte in SEARCH, sonst überspringen."""
    from backend import index_db
    s = FakeServer()
    s.boxes["INBOX"].add(b"From: a@x.de\r\nSubject: s\r\n\r\nx")
    _sync(s)
    with index_db.connect() as c:
        c.execute("UPDATE messages SET message_id=?", (mid,))
        m = c.execute("SELECT id FROM messages").fetchone()[0]
    conn = FakeIMAPW(s)
    searched = []
    orig = conn.uid
    conn.uid = lambda cmd, *a: (searched.append(a) if cmd.upper() == "SEARCH" else None) or orig(cmd, *a)
    from backend import actions
    assert actions.apply(ACC, conn, "delete", [m]) == {"done": 0, "skipped": 1}
    assert searched == [] and 1 in s.boxes["INBOX"].msgs


def test_gmail_mehrere_fundorte_nur_einmal_verschieben(archive):
    """Gmail: dieselbe Mail im Posteingang und in „Alle Nachrichten“ → nur ein Fundort wird verschoben."""
    s = FakeServer()
    s.box("Alle", special="\\All")
    s.box("Projekte")
    s.boxes["INBOX"].add(_mail(5))
    s.boxes["Alle"].add(_mail(5))
    _sync(s)
    r, _ = _run(s, "move", _mid(5), target="Projekte")
    assert r["done"] == 1 and len(s.boxes["Projekte"].msgs) == 1
    assert len(s.boxes["Alle"].msgs) + len(s.boxes["INBOX"].msgs) == 1


def test_select_fehler_arbeitet_nicht_im_vorigen_ordner(archive, srv):
    """Scheitert SELECT des zweiten Ordners, bleibt der erste ausgewählt. Dieselbe Mail (gleiche Message-ID) mit gleicher
    UID dort darf dann nicht versehentlich verändert werden."""
    srv.box("Kopie").add(_mail(0))                # UID 1 in „Kopie“ = Mail 0 (wie UID 1 im Posteingang)
    _sync(srv)
    conn = FakeIMAPW(srv)
    real = conn.select

    def sel(mb, readonly=False):
        if mb == '"Kopie"':
            return "NO", [b"busy"]
        return real(mb, readonly=readonly)
    conn.select = sel
    from backend import actions
    from backend import index_db
    with index_db.connect() as c:
        c.execute("DELETE FROM locations WHERE folder_id=(SELECT id FROM folders WHERE name='Papierkorb')")
    srv.boxes["INBOX"].msgs[1][1].discard("\\Seen")
    actions.apply(ACC, conn, "seen", [_mid(0)])
    assert "\\Seen" in srv.boxes["INBOX"].msgs[1][1]          # im Posteingang gesetzt (richtig)
    assert conn.selected is None or conn.selected.name != "Kopie"
    assert "\\Seen" not in srv.boxes["Kopie"].msgs[1][1]


def test_select_fehler_kein_schreiben_im_alten_ordner(archive, srv):
    """Reihenfolge: erst „Aaa“ (scheitert) – vorher war INBOX ausgewählt (z. B. vom vorigen Aufruf).
    Dann darf in INBOX nichts passieren."""
    srv.box("Aaa").add(_mail(0))
    _sync(srv)
    from backend import actions, index_db
    with index_db.connect() as c:          # nur der Fundort in „Aaa“ zählt für diese Mail
        c.execute("DELETE FROM locations WHERE folder_id=(SELECT id FROM folders WHERE name='INBOX') AND uid=1")
    conn = FakeIMAPW(srv)
    conn.select('"INBOX"', readonly=False)
    real = conn.select
    conn.select = lambda mb, readonly=False: ("NO", [b"busy"]) if mb == '"Aaa"' else real(mb, readonly=readonly)
    r = actions.apply(ACC, conn, "delete", [_mid(0)])
    assert r == {"done": 0, "skipped": 1}
    assert 1 in srv.boxes["INBOX"].msgs and srv.boxes["Papierkorb"].msgs == {}
