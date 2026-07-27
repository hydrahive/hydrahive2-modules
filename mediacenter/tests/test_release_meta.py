"""V2/A: Cover- und Metadaten aus den Newznab-Attributen.

Der Indexer liefert (live verifiziert 27.07.2026) coverurl, backdropurl, imdb,
tmdb, imdbtitle, imdbscore, imdbplot, genre, tvdbid, season/episode, artist/album.
V1 hat all das verworfen. V2 parst es in ein optionales ReleaseMeta.

SICHERHEIT: Der Indexer spiegelt den API-Schluessel in link/enclosure zurueck.
Jedes NEUE Feld muss deshalb durch release_contains_secret() — sonst reisst der
Ausbau das Loch wieder auf, das V1 geschlossen hat.
"""
from __future__ import annotations

from backend.models import RawRelease
from backend.newznab_xml import parse_search
from backend.redaction import release_contains_secret

_ATTR = '<newznab:attr name="{n}" value="{v}" />'


def _rss(*attrs: str, title: str = "Matrix.1999.German.1080p.BluRay-GRP") -> bytes:
    body = "\n      ".join(attrs)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:newznab="http://www.newznab.com/DTD/2010/feeds/attributes/" version="2.0">
  <channel>
    <item>
      <title>{title}</title>
      <guid isPermaLink="false">g-1</guid>
      <link>https://treasure-maps.com/getnzb/g-1</link>
      <pubDate>Sat, 26 Jul 2026 10:00:00 +0000</pubDate>
      <enclosure url="https://treasure-maps.com/getnzb/g-1" length="900" type="application/x-nzb" />
      {_ATTR.format(n="category", v="2140")}
      {_ATTR.format(n="size", v="900")}
      {_ATTR.format(n="guid", v="g-1")}
      {body}
    </item>
  </channel>
</rss>""".encode()


# --- 1. Film-Metadaten ------------------------------------------------------

def test_film_metadaten_werden_geparst():
    data = _rss(
        _ATTR.format(n="coverurl", v="https://picbit.io/movies_0242653-cover.webp"),
        _ATTR.format(n="backdropurl", v="https://picbit.io/movies_0242653-backdrop.webp"),
        _ATTR.format(n="imdb", v="0242653"),
        _ATTR.format(n="tmdb", v="605"),
        _ATTR.format(n="imdbtitle", v="The Matrix Revolutions"),
        _ATTR.format(n="imdbyear", v="2003"),
        _ATTR.format(n="imdbscore", v="6.7"),
        _ATTR.format(n="genre", v="Action, Adventure, Science Fiction"),
        _ATTR.format(n="imdbplot", v="Die Menschheit kaempft ums Ueberleben."),
    )
    meta = parse_search(data)[0].meta
    assert meta is not None
    assert meta.cover_url == "https://picbit.io/movies_0242653-cover.webp"
    assert meta.backdrop_url == "https://picbit.io/movies_0242653-backdrop.webp"
    assert meta.title_clean == "The Matrix Revolutions"
    assert meta.year == 2003
    assert meta.score == 6.7
    assert list(meta.genres) == ["Action", "Adventure", "Science Fiction"]
    assert meta.plot.startswith("Die Menschheit")
    assert meta.imdb_id == "0242653"
    assert meta.tmdb_id == "605"


def test_ohne_metadaten_bleibt_meta_none():
    """Rueckwaertskompatibel: V1-Releases ohne Zusatzattribute funktionieren weiter."""
    assert parse_search(_rss())[0].meta is None


def test_serien_metadaten():
    data = _rss(
        _ATTR.format(n="tvdbid", v="121361"),
        _ATTR.format(n="tvtitle", v="Foundation"),
        _ATTR.format(n="season", v="2"),
        _ATTR.format(n="episode", v="5"),
        _ATTR.format(n="coverurl", v="https://picbit.io/tv_121361-cover.webp"),
    )
    meta = parse_search(data)[0].meta
    assert meta.tvdb_id == "121361"
    assert meta.title_clean == "Foundation"
    assert meta.season == 2
    assert meta.episode == 5


def test_musik_metadaten():
    data = _rss(
        _ATTR.format(n="artist", v="Rammstein"),
        _ATTR.format(n="album", v="Zeit"),
        _ATTR.format(n="label", v="Universal"),
        _ATTR.format(n="coverurl", v="https://picbit.io/music_1-cover.webp"),
    )
    meta = parse_search(data)[0].meta
    assert meta.artist == "Rammstein"
    assert meta.album == "Zeit"
    assert meta.label == "Universal"


# --- 2. Cover-URL-Validierung (SSRF/Leak-Schutz) ---------------------------

# Ein zweites, gueltiges Attribut sorgt dafuer, dass meta nicht None ist —
# so pruefen die Tests gezielt die URL-Validierung statt "gar keine Metadaten".
_VALID = _ATTR.format(n="imdbtitle", v="Irgendein Film")


def test_cover_url_nur_https():
    data = _rss(_VALID, _ATTR.format(n="coverurl", v="http://picbit.io/x-cover.webp"))
    meta = parse_search(data)[0].meta
    assert meta.title_clean == "Irgendein Film"
    assert meta.cover_url is None


def test_cover_url_fremder_host_wird_verworfen():
    """Allowlist: sonst koennte der Indexer uns auf beliebige Hosts zeigen lassen."""
    data = _rss(_VALID, _ATTR.format(n="coverurl", v="https://evil.example/x.webp"))
    assert parse_search(data)[0].meta.cover_url is None


def test_nur_ungueltige_werte_ergeben_gar_keine_metadaten():
    """Wenn nach der Validierung nichts uebrig bleibt, ist meta None — die
    Oberflaeche faellt dann auf die V1-Darstellung zurueck."""
    data = _rss(_ATTR.format(n="coverurl", v="https://evil.example/x.webp"))
    assert parse_search(data)[0].meta is None


def test_cover_url_query_wird_entfernt():
    """Queryparameter koennten einen Schluessel mitfuehren — dieselbe Regel wie
    beim NZB-Abruf: alles nach dem Pfad wird verworfen."""
    data = _rss(_ATTR.format(n="coverurl", v="https://picbit.io/x-cover.webp?apikey=GEHEIM"))
    cover = parse_search(data)[0].meta.cover_url
    assert cover == "https://picbit.io/x-cover.webp"
    assert "GEHEIM" not in cover


def test_cover_url_mit_credentials_wird_verworfen():
    data = _rss(_VALID, _ATTR.format(n="coverurl", v="https://user:pw@picbit.io/x.webp"))
    assert parse_search(data)[0].meta.cover_url is None


# --- 3. Secret-Leak: die neuen Felder muessen mitgeprueft werden -----------

def test_release_contains_secret_prueft_auch_metadaten():
    """DER KERNTEST: V1 prueft nur title/guid/language/download_url. Wenn ein
    Secret in einem NEUEN Feld steht, muss der Filter trotzdem anschlagen."""
    from backend.models import ReleaseMeta

    release = RawRelease(
        title="sauber", guid="g", category_id=2140, size_bytes=1,
        language="de", published_at=None, download_url=None,
        meta=ReleaseMeta(plot="enthaelt GEHEIM im Text"),
    )
    assert release_contains_secret(release, "GEHEIM") is True


def test_release_ohne_secret_passiert_den_filter():
    from backend.models import ReleaseMeta

    release = RawRelease(
        title="sauber", guid="g", category_id=2140, size_bytes=1,
        language="de", published_at=None, download_url=None,
        meta=ReleaseMeta(plot="voellig unverfaenglich"),
    )
    assert release_contains_secret(release, "GEHEIM") is False


# --- 4. Robustheit: kaputte Werte duerfen nichts umwerfen ------------------

def test_unsinnige_werte_werden_still_verworfen():
    data = _rss(
        _VALID,
        _ATTR.format(n="imdbscore", v="keine-zahl"),
        _ATTR.format(n="imdbyear", v="99999"),
        _ATTR.format(n="season", v="-3"),
    )
    meta = parse_search(data)[0].meta
    assert meta.score is None
    assert meta.year is None
    assert meta.season is None


def test_ueberlanger_plot_wird_gekuerzt():
    """Ein langer Plot darf das Release NICHT verwerfen. Der generische
    512-Zeichen-Deckel fuer Attribute haette den Treffer sonst verschwinden
    lassen — Fliesstext wird stattdessen gekuerzt."""
    results = parse_search(_rss(_ATTR.format(n="imdbplot", v="A" * 900)))
    assert len(results) == 1, "langer Plot darf den Treffer nicht verschlucken"
    assert len(results[0].meta.plot) <= 500


def test_absurd_langer_plot_verwirft_das_release_doch():
    """Die Ausnahme ist begrenzt: jenseits von 4096 Zeichen gilt der Wert als
    kaputt/boesartig und das Release fliegt raus."""
    assert parse_search(_rss(_ATTR.format(n="imdbplot", v="A" * 5000))) == []


def test_genres_werden_begrenzt():
    data = _rss(_ATTR.format(n="genre", v="A, B, C, D, E, F, G, H"))
    assert len(parse_search(data)[0].meta.genres) <= 5


def test_score_ausserhalb_der_skala_wird_verworfen():
    data = _rss(_VALID, _ATTR.format(n="imdbscore", v="42"))
    assert parse_search(data)[0].meta.score is None


# --- 5. extended=1: ohne den Parameter liefert der Indexer KEINE Metadaten --

def test_suchanfrage_fordert_erweiterte_attribute_an():
    """Live-Befund: der Indexer sendet coverurl/imdb/genre nur mit extended=1.
    Ohne diesen Parameter waere der ganze Cover-Ausbau wirkungslos."""
    from backend.models import SearchRequest
    from backend.newznab import build_search_params

    params = build_search_params(SearchRequest(query="Matrix", media_type="movie"))
    assert params.get("extended") == "1"
