"""M1 Schritt 8, Teil 2: Suche ohne FTS5, Anhang-/Datumsfilter, Rollen, Blättern in der Datenbank."""
# ruff: noqa: F811 - pytest-Fixtures aus _search_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest  # noqa: F401
from _search_base import A1, A2, ADDR, _mail, _q, mails  # noqa: F401 - Fixtures/Hilfen


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


def test_mit_fts_blaettert_die_datenbank(mails, monkeypatch):
    """Mit FTS5 holt die Abfrage nur die angezeigte Seite (LIMIT/OFFSET in SQL) – nicht alle Treffer in den Speicher."""
    from backend import index_db, search
    seen = []
    real = index_db.connect

    class Spy:
        def __init__(self, c): self.c = c
        def execute(self, sql, *a):
            seen.append(sql)
            return self.c.execute(sql, *a)
        def __getattr__(self, n): return getattr(self.c, n)

    from contextlib import contextmanager

    @contextmanager
    def spy():
        with real() as c:
            yield Spy(c)
    monkeypatch.setattr(index_db, "connect", spy)
    r = search.search({A1: ADDR[A1]}, "termin", limit=1, offset=1)
    assert r["total"] == 2 and len(r["items"]) == 1
    sel = [s for s in seen if s.lstrip().upper().startswith("SELECT M.ID")]
    assert sel and all("LIMIT" in s.upper() for s in sel)
    assert any("COUNT(*)" in s.upper() for s in seen)
