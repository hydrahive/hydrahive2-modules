"""Suche (FTS5 + exakte Normbezeichnung). L0: Fachbegriffe 19/20 in den Top 5 (Spec §6a)."""
from __future__ import annotations

import pytest
from backend import corpus_store as store
from backend import search
from backend.gii_parse import parse_law
from conftest import fixture_xml


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
    changed = fixture_xml("bgb").replace("unverzüglich anzuzeigen".encode(), b"binnen einer Woche anzuzeigen")
    store.save_law(parse_law("bgb", changed), changed, fetched_at="2026-11-02T03:30:00Z", pinned=True)
    hits = [h for h in search.search("Mangel Mietsache Anzeige Mieter") if h["enbez"] == "§ 536c"]
    assert len(hits) == 1


def test_title_weighs_more_than_text(corpus):
    """„Widerrufsrecht Verbrauchervertrag“: § 355 BGB hat die Wörter im Titel, §§ 356d/e/f nur im Text.
    Auf dem echten Korpus stand ungewichtet § 356e vorne (L0, 20.10.2026). bm25 hängt von der Korpusgröße ab –
    daher hier der Vorsprung des Titel-Treffers statt nur der Platz. Gemessen auf dieser Fixture (20.10.2026):
    Titel 8 → 2,97-fach, Titel 4 → 2,77, Titel 2 → 2,44, alle 1 → 2,0. Schwelle 2,9 trennt das gewählte Gewicht."""
    assert _ids(search.search("Widerrufsrecht Verbrauchervertrag", limit=3))[0] == ("BGB", "§ 355")
    assert search.BM25_WEIGHTS[2] >= 4 * search.BM25_WEIGHTS[4]          # Titel ≥ 4 × Text
    assert search.BM25_WEIGHTS[3] > search.BM25_WEIGHTS[4]               # Gliederung > Text (Normen ohne Titel)
    from hydrahive.db.connection import db
    with db() as c:
        def lead(w):
            rows = c.execute(f"SELECT n.enbez, bm25(module_legal_norms_fts, {', '.join(map(str, w))}) "
                             "FROM module_legal_norms_fts JOIN module_legal_norms n ON n.id = module_legal_norms_fts.rowid "
                             "WHERE module_legal_norms_fts MATCH ? AND n.valid_to IS NULL ORDER BY 2 LIMIT 2",
                             ('"widerrufsre"* OR "verbraucherver"*',)).fetchall()
            return rows[0][1] / rows[1][1]
        assert lead(search.BM25_WEIGHTS) >= 2.9


def test_limit_is_capped():
    """Mehr als 20 passende Normen anlegen – limit=500 darf trotzdem höchstens MAX_LIMIT liefern."""
    from backend.gii_parse import Law, Norm
    law = Law(key="testg", abbr="TestG", title="Testgesetz", stand="",
              norms=[Norm("TestG", f"§ {i}", f"d{i}", f"Frist Nummer {i}", "", f"Eine Frist von {i} Tagen.", i)
                     for i in range(1, 31)])
    store.save_law(law, b"x", fetched_at="2026-10-20T03:30:00Z", pinned=False)
    assert len(search.search("Frist", law="TestG", limit=500)) == search.MAX_LIMIT == 20


def test_citation_query_lists_norms_that_cite_it_not_noise(corpus):
    """Live hydratest 20.10.2026: „§ 536c BGB“ brachte unter dem exakten Treffer „Anhang EV ZPO/HeizkostenV“, weil
    „bgb“ fast überall vorkommt. Nach einer Normbezeichnung zählen nur Normen, die genau diese Nummer zitieren."""
    hits = search.search("§ 536 BGB")
    assert hits[0]["match"] == "exact" and hits[0]["enbez"] == "§ 536"
    rest = hits[1:]
    assert rest, "§ 536c zitiert „§ 536“ – muss als Querverweis erscheinen"
    assert all("536" in h["snippet"] for h in rest)
    assert ("BGB", "§ 536c") in _ids(rest)
    assert all(h["match"] == "cites" for h in rest)
