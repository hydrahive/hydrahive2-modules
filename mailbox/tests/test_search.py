"""M1 Schritt 8: Suche – Volltext + Filter, nur eigene Konten, sichere Eingaben, gleicher Treffer ohne FTS5."""
from __future__ import annotations

import pytest
from conftest import eml

A1, A2 = "acc1", "acc2"
ADDR = {A1: "till@example.net", A2: "frau@example.net"}


def _mail(n, subject, frm="anna@example.org", to="till@example.net", date="Tue, 20 Oct 2026 09:00:00 +0000",
          body="Text", attach=False):
    head = (f"From: {frm}\r\nTo: {to}\r\nSubject: {subject}\r\nMessage-ID: <s{n}@x>\r\nDate: {date}\r\n")
    if not attach:
        return (head + f"\r\n{body}\r\n").encode()
    return (head + "Content-Type: multipart/mixed; boundary=B\r\n\r\n--B\r\nContent-Type: text/plain\r\n\r\n"
            f"{body}\r\n--B\r\nContent-Type: application/pdf\r\nContent-Disposition: attachment; filename=r.pdf\r\n\r\n"
            "xx\r\n--B--\r\n").encode()


@pytest.fixture
def mails(archive):
    from backend import parse, store
    inbox, sent = store.folder(A1, "INBOX", role="inbox"), store.folder(A1, "Gesendet", role="sent")
    other = store.folder(A2, "INBOX", role="inbox")
    items = [
        (A1, inbox, 1, _mail(1, "Termin morgen", body="Treffen im Büro um zehn")),
        (A1, inbox, 2, _mail(2, "Rechnung Oktober", frm="buchhaltung@firma.de", attach=True,
                             date="Mon, 05 Jan 2015 10:00:00 +0000")),
        (A1, sent, 3, _mail(3, "Re: Termin morgen", frm="till@example.net", to="anna@example.org", body="Passt mir",
                            date="Tue, 20 Oct 2026 09:30:00 +0000")),
        (A1, inbox, 4, eml("latin1")),
        (A2, other, 1, _mail(5, "Termin geheim", body="nur für Frau")),
    ]
    ids = {}
    for acc, fid, uid, raw in items:
        p = parse.parse(raw)
        ids[p.subject] = store.add_message(acc, fid, uid, p, path=f"x/{uid}.eml", size=len(raw), flags=set())
    return {"ids": ids, "inbox": inbox, "sent": sent}


def _q(q, accounts=(A1,), **kw):
    from backend import search
    return [r["subject"] for r in search.search({a: ADDR[a] for a in accounts}, q, **kw)["items"]]


def test_volltext_findet_auch_text(mails):
    assert sorted(_q("termin")) == ["Re: Termin morgen", "Termin morgen"]
    assert _q("büro") == ["Termin morgen"], "Treffer im Text, nicht nur im Betreff"


def test_nur_eigene_konten(mails):
    assert "Termin geheim" not in _q("termin")
    assert _q("geheim") == []
    assert _q("geheim", accounts=(A2,)) == ["Termin geheim"]


def test_ohne_konten_nichts(mails):
    from backend import search
    assert search.search({}, "termin")["items"] == []


def test_umlaut_ohne_akzent_und_praefix(mails):
    assert _q("koln") == ["Grüße aus Köln 😃"]
    assert _q("Rechn") == ["Rechnung Oktober"], "Wortanfang reicht"


def test_filter(mails):
    assert _q("von:buchhaltung") == ["Rechnung Oktober"]
    assert _q("an:anna@example.org") == ["Re: Termin morgen"]
    assert _q("betreff:rechnung") == ["Rechnung Oktober"]
    assert _q("hat:anhang") == ["Rechnung Oktober"]
    assert _q("vor:2016-01-01") == ["Rechnung Oktober", "Grüße aus Köln 😃"]
    assert "Rechnung Oktober" not in _q("nach:2016-01-01")
    assert _q("ordner:Gesendet") == ["Re: Termin morgen"]
    assert _q("konto:frau termin", accounts=(A1, A2)) == ["Termin geheim"]


def test_filter_und_text_kombiniert(mails):
    assert _q("termin von:till") == ["Re: Termin morgen"]


def test_phrase(mails):
    assert sorted(_q('"termin morgen"')) == ["Re: Termin morgen", "Termin morgen"]
    assert _q('"morgen termin"') == []


def test_neueste_zuerst(mails):
    assert _q("") == ["Re: Termin morgen", "Termin morgen", "Rechnung Oktober", "Grüße aus Köln 😃"]


@pytest.mark.parametrize("q", ['"', '*', 'NEAR', 'termin AND', 'a OR b', '-x', 'col:term', '"""', '(', ')', "'", "^x",
                               "termin*", "von:", "vor:kaputt", "x" * 1000, "\x00"])
def test_sonderzeichen_brechen_nicht(mails, q):
    from backend import search
    search.search({A1: ADDR[A1]}, q)


def test_operatoren_sind_woerter(mails):
    """„OR“ ist kein Operator: Suche nach „termin OR rechnung“ verlangt alle drei Wörter."""
    assert _q("termin OR rechnung") == []


def test_ordner_und_seiten(mails):
    from backend import search
    r = search.search({A1: ADDR[A1]}, "", folder_id=mails["inbox"], limit=2)
    assert len(r["items"]) == 2 and r["total"] == 3
    r2 = search.search({A1: ADDR[A1]}, "", folder_id=mails["inbox"], limit=2, offset=2)
    assert len(r2["items"]) == 1


def test_fremder_ordner_leer(mails):
    from backend import search, store
    other = store.folder(A2, "INBOX", role="inbox")
    assert search.search({A1: ADDR[A1]}, "", folder_id=other)["items"] == []


def test_nur_auf_server_geloeschte(mails):
    from backend import search, store
    store.drop_locations(mails["inbox"], keep_uids={1, 4})
    store.reconcile(A1)
    r = search.search({A1: ADDR[A1]}, "", only_deleted=True)
    assert [x["subject"] for x in r["items"]] == ["Rechnung Oktober"] and r["items"][0]["deleted_on_server"] == 1
    assert "Rechnung Oktober" in _q("rechnung"), "Archiv bleibt durchsuchbar"


def test_felder_der_treffer(mails):
    from backend import search
    it = search.search({A1: ADDR[A1]}, "rechnung")["items"][0]
    assert it["has_attachments"] is True and it["account"] == "till@example.net" and "sha256" not in it
    assert set(it) >= {"id", "date", "from_addr", "subject", "snippet", "seen", "flagged", "thread_key", "folder"}


def test_grenze(mails):
    from backend import search
    assert search.search({A1: ADDR[A1]}, "", limit=10_000)["limit"] == search.LIMIT_MAX


def test_ohne_fts_gleiche_treffer(mails, monkeypatch):
    from backend import search
    qs = ("termin", "rechnung", "von:buchhaltung", "koln", "köln", "Rechn", '"termin morgen"', "büro", "buro", "zehn")
    with_fts = {q: sorted(_q(q)) for q in qs}
    with monkeypatch.context() as m:
        m.setattr(search, "_has_fts", lambda c: False)
        without = {q: sorted(_q(q)) for q in qs}
    assert with_fts == without
    assert with_fts["koln"] == ["Grüße aus Köln 😃"] and with_fts["buro"] == ["Termin morgen"], "Test prüft wirklich etwas"


def test_nur_eingebettetes_bild_ist_kein_anhang(mails):
    from backend import parse, store
    raw = (b"From: x@y.de\r\nSubject: Logo-Mail\r\nMessage-ID: <logo@y>\r\nContent-Type: multipart/related; boundary=B\r\n\r\n"
           b"--B\r\nContent-Type: text/html\r\n\r\n<img src=cid:l1>\r\n--B\r\nContent-Type: image/png\r\n"
           b"Content-ID: <l1>\r\nContent-Disposition: inline\r\n\r\nxx\r\n--B--\r\n")
    store.add_message(A1, mails["inbox"], 20, parse.parse(raw), path="x/20.eml", size=len(raw), flags=set())
    assert _q("hat:anhang") == ["Rechnung Oktober"]


def test_vor_schliesst_mails_ohne_datum_aus(mails):
    from backend import parse, store
    raw = b"From: x@y.de\r\nSubject: Ohne Datum\r\nMessage-ID: <nd@y>\r\n\r\nx\r\n"
    store.add_message(A1, mails["inbox"], 21, parse.parse(raw), path="x/21.eml", size=len(raw), flags=set())
    assert "Ohne Datum" not in _q("vor:2030-01-01")


def test_platzhalter_im_filter_sind_zeichen(mails):
    assert _q("von:%") == [] and _q("von:_") == [] and _q("betreff:%rechnung") == []


def test_fts_ausdruck_nur_in_anfuehrungszeichen():
    """Zweite Schicht: selbst wenn ein Operatorwort durchrutscht, steht es in Anführungszeichen."""
    from backend import query
    q = query.Query(words=["or", "near", "termin"], phrases=[["a", "b"]])
    assert query.fts_expr(q) == '"or"* AND "near"* AND "termin"* AND "a b"'


def test_ohne_konten_frueh_raus(monkeypatch):
    """Keine Konten → gar keine Abfrage (nicht erst über einen leeren IN-Filter)."""
    from backend import index_db, search
    monkeypatch.setattr(index_db, "connect", lambda: (_ for _ in ()).throw(AssertionError("keine DB-Abfrage")))
    assert search.search({}, "termin")["items"] == []


def test_nur_posteingaenge_im_backend(mails):
    """„Alle Posteingänge“: Filter im Backend (sonst stimmen Seiten und Gesamtzahl nicht)."""
    from backend import search
    r = search.search({A1: ADDR[A1]}, "", role="inbox", limit=2)
    assert r["total"] == 3 and len(r["items"]) == 2
    assert all(x["folder"] == "INBOX" for x in r["items"])
    assert "Re: Termin morgen" not in [x["subject"] for x in search.search({A1: ADDR[A1]}, "", role="inbox")["items"]]


def test_rolle_unbekannt_wird_ignoriert(mails):
    from backend import search
    assert search.search({A1: ADDR[A1]}, "", role="'; DROP TABLE messages; --")["total"] == 4
