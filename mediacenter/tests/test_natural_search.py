"""V2/C: natuerlichsprachige Suche am Endpunkt.

Der Parser laeuft SERVERSEITIG in der bestehenden /search-Route. Damit
profitieren Oberflaeche UND Agenten davon, ohne dass die Logik doppelt
existiert.

Wichtig: explizite Angaben des Aufrufers gewinnen immer gegen den Parser —
er ergaenzt nur, was nicht gesetzt ist.
"""
from __future__ import annotations

from backend.models import SearchRequest
from backend.natural_search import apply_natural_language


def test_jahr_wird_uebernommen_und_query_bereinigt():
    enriched, parsed = apply_natural_language(
        SearchRequest(query="Matrix von 1999", media_type="movie"))
    assert enriched.query == "Matrix"
    assert enriched.year == 1999
    assert "year" in parsed.recognized


def test_staffel_wird_uebernommen():
    enriched, _ = apply_natural_language(
        SearchRequest(query="Foundation Staffel 2", media_type="tv"))
    assert enriched.query == "Foundation"
    assert enriched.season == 2


def test_explizite_angabe_schlaegt_den_parser():
    """Der Nutzer hat 2020 im Formularfeld stehen — der Text sagt 1999.
    Das Formular gewinnt, sonst ueberschreibt Magie eine bewusste Eingabe."""
    enriched, _ = apply_natural_language(
        SearchRequest(query="Matrix von 1999", media_type="movie", year=2020))
    assert enriched.year == 2020
    assert enriched.query == "Matrix"


def test_medientyp_des_aufrufers_bleibt_erhalten():
    """media_type ist im Request Pflicht — der Parser darf ihn nie umbiegen."""
    enriched, _ = apply_natural_language(
        SearchRequest(query="Hörbuch Der Hobbit", media_type="movie"))
    assert enriched.media_type == "movie"


def test_ohne_erkennbares_bleibt_die_anfrage_unveraendert():
    original = SearchRequest(query="Irgendein Titel", media_type="movie")
    enriched, parsed = apply_natural_language(original)
    assert enriched.query == "Irgendein Titel"
    assert parsed.recognized == []


def test_filter_der_nicht_zum_medientyp_passt_wird_verworfen():
    """season gilt nur fuer tv — bei einem Film darf der Parser ihn nicht
    setzen, sonst schlaegt die Modellvalidierung fehl."""
    enriched, _ = apply_natural_language(
        SearchRequest(query="Matrix Staffel 2", media_type="movie"))
    assert enriched.season is None


def test_query_bleibt_gueltig_wenn_nur_schluesselwoerter_gesucht_werden():
    """Nach dem Bereinigen muss der Suchbegriff die Mindestlaenge behalten."""
    enriched, _ = apply_natural_language(
        SearchRequest(query="Staffel 2", media_type="tv"))
    assert len(enriched.query) >= 2
