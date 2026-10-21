"""M1 Schritt 8: Suche – Volltext + Filter, nur eigene Konten, sichere Eingaben, gleicher Treffer ohne FTS5."""
# ruff: noqa: F811 - pytest-Fixtures aus _search_base werden als gleichnamige Parameter genutzt
from __future__ import annotations

import pytest
from _search_base import A1, A2, ADDR, _mail, _q, mails  # noqa: F401 - Fixtures/Hilfen


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


