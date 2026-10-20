"""Suche (FTS5 + exakte Normbezeichnung). L0: Fachbegriffe 19/20 in den Top 5 (Spec §6a)."""
from __future__ import annotations

import pytest
from conftest import fixture_xml

from backend import corpus_store as store
from backend import search
from backend.gii_parse import parse_law


@pytest.fixture
def corpus():
    for key in ("bgb", "vwgo", "owig_1968", "betrkv"):
        xml = fixture_xml(key)
        store.save_law(parse_law(key, xml), xml, fetched_at="2026-10-20T03:30:00Z", pinned=True)


def _ids(hits):
    return [(h["abbr"], h["enbez"]) for h in hits]


def test_exact_citation_comes_first(corpus):
    hits = search.search("§ 536c BGB")
    assert _ids(hits)[0] == ("BGB", "§ 536c")
    assert hits[0]["match"] == "exact"


@pytest.mark.parametrize("query,expected", [
    ("Mangel Mietsache Anzeige Mieter", ("BGB", "§ 536c")),
    ("Mietsicherheit", ("BGB", "§ 551")),
    ("Aufstellung der Betriebskosten", ("BetrKV", "§ 2")),
    ("Einspruch Bußgeldbescheid", ("OWiG", "§ 67")),
    ("Widerspruch Frist Verwaltungsakt", ("VwGO", "§ 70")),
    ("Unterhaltsverpflichtete Verwandte gerader Linie", ("BGB", "§ 1601")),
])
def test_legal_terms_find_the_norm_in_top_3(corpus, query, expected):
    assert expected in _ids(search.search(query, limit=3))


def test_prefix_and_umlaut_forms(corpus):
    assert ("BGB", "§ 536c") in _ids(search.search("Mängelanzeige"))


def test_filter_by_law(corpus):
    hits = search.search("Frist", law="VwGO")
    assert hits and {h["abbr"] for h in hits} == {"VwGO"}


def test_hits_show_gliederung_when_no_title(corpus):
    hit = next(h for h in search.search("Widerspruch Frist Verwaltungsakt") if h["enbez"] == "§ 70")
    assert hit["title"] == ""
    assert "Anfechtungs- und Verpflichtungsklagen" in hit["heading"]


def test_snippet_is_short_and_from_text(corpus):
    hit = search.search("Mangel Mietsache Anzeige Mieter", limit=1)[0]
    assert 0 < len(hit["snippet"]) <= 300


def test_limit_and_empty_query(corpus):
    assert len(search.search("Frist", limit=2)) == 2
    with pytest.raises(search.SearchError):
        search.search("der die das")                      # nur Füllwörter → keine Suchwörter
    with pytest.raises(search.SearchError):
        search.search("   ")
    with pytest.raises(search.SearchError):
        search.search('"""*')                               # nur Sonderzeichen → keine Suchwörter


def test_fts_syntax_cannot_be_injected(corpus):
    for evil in ['Mangel" OR text:*', "NEAR(Mangel Mieter)", "abbr:BGB", "Mangel*)("]:
        search.search(evil)                                 # darf keinen sqlite-Fehler werfen


def test_old_versions_are_not_found(corpus):
    changed = fixture_xml("bgb").replace("unverzüglich anzuzeigen".encode(), "binnen einer Woche anzuzeigen".encode())
    store.save_law(parse_law("bgb", changed), changed, fetched_at="2026-11-02T03:30:00Z", pinned=True)
    hits = [h for h in search.search("Mangel Mietsache Anzeige Mieter") if h["enbez"] == "§ 536c"]
    assert len(hits) == 1
