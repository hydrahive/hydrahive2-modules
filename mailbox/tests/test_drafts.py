"""M2 Schritt 6: Entwürfe – lokal im Index (nur der Ersteller), Kopie im Entwürfe-Ordner des Servers, beim Ändern
ersetzt (alte Kopie gezielt entfernt), beim Senden/Löschen weg. Ohne Entwürfe-Ordner nur lokal."""
from __future__ import annotations

import pytest
from _fake_imap import FakeServer
from _fake_imap_write import FakeIMAPW

ACC = {"id": "acc1", "address": "till@example.net", "sender_name": "Till", "signature": "", "imap_host": "imap.x.de",
       "username": "till@example.net"}
CAPS = ("MOVE", "UIDPLUS", "UNSELECT")


@pytest.fixture
def srv():
    s = FakeServer()
    s.box("Entwürfe", special="\\Drafts")
    return s


def _known(srv):
    from _fake_imap import FakeIMAP
    from backend import fetch
    fetch.sync_account(ACC, FakeIMAP(srv))


def _open(srv, caps=CAPS):
    return lambda acc: FakeIMAPW(srv, caps=caps)


def _save(srv, user="alice", draft_id=None, caps=CAPS, **fields):
    from backend import drafts
    data = {"to": "anna@example.org", "subject": "Entwurf", "body": "Hallo", **fields}
    return drafts.save(user, ACC, data, draft_id=draft_id, password="pw", open_imap=_open(srv, caps))


def _server_drafts(srv):
    return [raw for raw, _ in srv.boxes["Entwürfe"].msgs.values()]


def test_anlegen_lokal_und_auf_dem_server(archive, srv):
    from backend import drafts
    _known(srv)
    d = _save(srv)
    assert d["subject"] == "Entwurf" and d["server"] == "ok"
    got = drafts.get("alice", d["id"])
    assert got["to"] == "anna@example.org" and got["body"] == "Hallo"
    raws = _server_drafts(srv)
    assert len(raws) == 1 and b"Subject: Entwurf" in raws[0]
    flags = list(srv.boxes["Entwürfe"].msgs.values())[0][1]
    assert "\\Draft" in flags and "\\Seen" in flags


def test_aendern_ersetzt_server_kopie(archive, srv):
    _known(srv)
    d = _save(srv)
    d2 = _save(srv, draft_id=d["id"], subject="Neu")
    assert d2["id"] == d["id"]
    raws = _server_drafts(srv)
    assert len(raws) == 1 and b"Subject: Neu" in raws[0] and srv.full_expunges == 0


def test_server_kopie_ohne_uidplus_bleibt_markiert(archive, srv):
    _known(srv)
    d = _save(srv, caps=("MOVE",))
    _save(srv, draft_id=d["id"], subject="Neu", caps=("MOVE",))
    msgs = list(srv.boxes["Entwürfe"].msgs.values())
    live = [raw for raw, fl in msgs if "\\Deleted" not in fl]
    assert len(live) == 1 and b"Subject: Neu" in live[0] and srv.full_expunges == 0


def test_nur_eigene_entwuerfe(archive, srv):
    from backend import drafts
    _known(srv)
    d = _save(srv, user="alice")
    assert drafts.get("bob", d["id"]) is None
    assert drafts.list_for("bob") == [] and [x["id"] for x in drafts.list_for("alice")] == [d["id"]]
    with pytest.raises(drafts.DraftError):
        _save(srv, user="bob", draft_id=d["id"], subject="geklaut")
    assert drafts.get("alice", d["id"])["subject"] == "Entwurf"
    assert drafts.delete("bob", d["id"], ACC, password="pw", open_imap=_open(srv)) is False


def test_loeschen_entfernt_server_kopie(archive, srv):
    from backend import drafts
    _known(srv)
    d = _save(srv)
    assert drafts.delete("alice", d["id"], ACC, password="pw", open_imap=_open(srv)) is True
    assert drafts.get("alice", d["id"]) is None and _server_drafts(srv) == []


def test_ohne_entwuerfe_ordner_nur_lokal(archive):
    s = FakeServer()
    _known(s)
    logins = s.logins
    d = _save(s)
    assert d["server"] == "local_only" and s.appends == [] and s.logins == logins, "gar nicht erst verbinden"


def test_server_nicht_erreichbar_entwurf_bleibt_lokal(archive, srv):
    from backend import drafts
    _known(srv)

    def boom(acc):
        raise OSError("down")
    d = drafts.save("alice", ACC, {"to": "", "subject": "x", "body": "y"}, password="pw", open_imap=boom)
    assert d["server"] == "local_only" and drafts.get("alice", d["id"])["body"] == "y"


def test_unvollstaendige_empfaenger_erlaubt(archive, srv):
    """Ein Entwurf darf halbe Adressen haben – geprüft wird erst beim Senden. Server-Kopie dann ohne die Kopfzeile."""
    _known(srv)
    d = _save(srv, to="anna@exa")
    assert d["to"] == "anna@exa"
    raws = _server_drafts(srv)
    assert len(raws) == 1 and b"\nTo:" not in raws[0]


@pytest.mark.parametrize("field, value", [("subject", "x\r\nBcc: a@b.de"), ("body", "x" * 1_000_001),
                                          ("mode", "boese"), ("to", "a@b.de\r\nX: 1")])
def test_eingaben_begrenzt(archive, srv, field, value):
    from backend import drafts
    _known(srv)
    with pytest.raises(drafts.DraftError):
        _save(srv, **{field: value})


def test_entwurf_nicht_ins_archiv(archive, srv):
    """Entwürfe sind Zwischenstände – sie landen nicht als Mails im Archiv (erst die gesendete Fassung)."""
    from backend import index_db
    _known(srv)
    _save(srv)
    with index_db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0


def test_loeschen_ueber_anderes_konto_abgelehnt(archive, srv):
    from backend import drafts
    _known(srv)
    d = _save(srv)
    other = {**ACC, "id": "acc2"}
    assert drafts.delete("alice", d["id"], other, password="pw", open_imap=_open(srv)) is False
    assert drafts.get("alice", d["id"]) is not None and len(_server_drafts(srv)) == 1


def test_gespeicherte_message_id_wird_vor_search_geprueft(archive, srv):
    """Verteidigung in der Tiefe: auch eine (manipulierte) gespeicherte Message-ID kommt nie roh in SEARCH."""
    from backend import drafts, index_db
    _known(srv)
    d = _save(srv)
    with index_db.connect() as c:
        c.execute("UPDATE drafts SET server_message_id=? WHERE id=?", ('<a" OR ALL "b>', d["id"]))
    conn = FakeIMAPW(srv, caps=CAPS)
    searched = []
    orig = conn.uid
    conn.uid = lambda cmd, *a: (searched.append(a) if cmd.upper() == "SEARCH" else None) or orig(cmd, *a)
    assert drafts.delete("alice", d["id"], ACC, password="pw", open_imap=lambda acc: conn) is True
    assert searched == [] and len(_server_drafts(srv)) == 1
