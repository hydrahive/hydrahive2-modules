"""Befund 21.10.2026 (M2): UIDVALIDITY wurde nie gespeichert/geprüft. Neue UIDs nach einem Wechsel können mit alten
übereinstimmen – dann hielt der Abgleich eine andere Mail für bekannt und archivierte sie nie (RFC 3501 §2.3.1.1)."""
from __future__ import annotations

from _fetch_base import _count, _mail, _sync, server  # noqa: F401 - Fixture


def test_uidvalidity_wechsel_mit_gleichen_uids_archiviert_neue_mail(archive, server):  # noqa: F811
    box = server.boxes["INBOX"]
    box.add(_mail(1))                       # UID 1 = Mail 1
    _sync(server)
    box.msgs.clear()
    box.uidvalidity, box.next_uid = 2000, 1
    box.add(_mail(2))                       # UID 1 = jetzt eine ANDERE Mail
    _sync(server)
    assert _count("message_id='<m2@example.org>'") == 1, "neue Mail muss ins Archiv"
    assert _count("message_id='<m1@example.org>' AND deleted_on_server=1") == 1, "alte bleibt, als nur-Archiv"


def test_uidvalidity_wird_gespeichert(archive, server):  # noqa: F811
    from backend import index_db
    server.boxes["INBOX"].add(_mail(1))
    _sync(server)
    with index_db.connect() as c:
        assert c.execute("SELECT uidvalidity FROM folders WHERE name='INBOX'").fetchone()[0] == 1000


def test_ohne_uidvalidity_antwort_bleibt_alles(archive, server):  # noqa: F811
    """Server liefert keinen UIDVALIDITY-Wert (kaputt/selten): nichts vergessen, kein Neuladen aller Mails."""
    from backend import store
    server.boxes["INBOX"].add(_mail(1))
    _sync(server)
    from backend import index_db
    with index_db.connect() as c:
        fid = c.execute("SELECT id FROM folders WHERE name='INBOX'").fetchone()[0]
    assert store.check_uidvalidity(fid, 0) is False
    assert store.known_uids(fid) == {1}
    server.body_fetches = 0
    _sync(server)
    assert server.body_fetches == 0
