"""M2 Schritt 7 (Teil 2): Aktionen – Grenzfälle: fremde Ordner, verschwundene Ordner, böse Message-IDs, Gmail-Labels,
gescheitertes SELECT. Hilfen aus test_actions.py."""
from __future__ import annotations

import pytest
from _fake_imap import FakeServer
from _fake_imap_write import FakeIMAPW
from _fetch_base import ACC, _mail
from test_actions import _mid, _run, _sync, srv  # noqa: F401 - Fixture


def test_ziel_nur_aus_eigenen_ordnern(archive, srv):  # noqa: F811
    """Ziel muss ein bekannter Ordner DIESES Kontos sein – ein gleichnamiger Ordner eines anderen Kontos zählt nicht."""
    from backend import actions, store
    _sync(srv)
    store.folder("fremd", "Nur-Fremd")
    srv.box("Nur-Fremd")
    with pytest.raises(actions.ActionError):
        _run(srv, "move", _mid(0), target="Nur-Fremd")
    assert srv.boxes["Nur-Fremd"].msgs == {}


def test_ordner_auf_dem_server_weg_wird_uebersprungen(archive, srv):  # noqa: F811
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


def test_select_fehler_arbeitet_nicht_im_vorigen_ordner(archive, srv):  # noqa: F811
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


def test_select_fehler_kein_schreiben_im_alten_ordner(archive, srv):  # noqa: F811
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
