"""V2/A: Metadaten in der API-Antwort + Gruppierung nach Titel.

Der eigentliche Radarr-Effekt: ein Film mit acht Fassungen erscheint als EINE
Karte mit acht Fassungen — statt achtmal in einer flachen Liste.

Gruppierungsschluessel: imdb/tmdb/tvdb-ID, sonst normalisierter Titel+Jahr.
"""
from __future__ import annotations

from datetime import datetime, timezone

from backend.models import ProfileDecision, RawRelease, ReleaseMeta
from backend.search_grouping import group_results
from backend.service import _result_out

_NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def _decision(title: str, *, imdb: str | None = None, score: int = 10,
              year: int | None = None, cover: str | None = None) -> ProfileDecision:
    meta = ReleaseMeta(imdb_id=imdb, year=year, cover_url=cover,
                       title_clean="Matrix" if imdb else None)
    release = RawRelease(
        title=title, guid=f"g-{title}", category_id=2140, size_bytes=1000,
        language="de", published_at=_NOW, download_url="https://treasure-maps.com/x",
        meta=meta if (imdb or year or cover) else None,
    )
    return ProfileDecision(release, "movie", "eligible", ("language_confirmed",),
                           "de", "1080", None, None, score)


# --- 1. Metadaten landen in der API-Antwort --------------------------------

def test_result_out_reicht_metadaten_durch():
    out = _result_out("till", _decision("Matrix.1999.German.1080p", imdb="0133093",
                                        year=1999, cover="https://picbit.io/c.webp"), _NOW)
    assert out.meta is not None
    assert out.meta.imdb_id == "0133093"
    assert out.meta.cover_url == "https://picbit.io/c.webp"
    assert out.meta.year == 1999


def test_result_out_ohne_metadaten_bleibt_none():
    """Rueckwaertskompatibel — V1-Clients sehen einfach kein meta."""
    assert _result_out("till", _decision("Alt.Release"), _NOW).meta is None


# --- 2. Gruppierung ---------------------------------------------------------

def test_gleiche_imdb_id_wird_zu_einer_gruppe():
    outs = [
        _result_out("till", _decision("Matrix.1080p", imdb="0133093", score=10), _NOW),
        _result_out("till", _decision("Matrix.2160p", imdb="0133093", score=20), _NOW),
        _result_out("till", _decision("Matrix.720p", imdb="0133093", score=5), _NOW),
    ]
    groups = group_results(outs)
    assert len(groups) == 1
    assert len(groups[0].releases) == 3


def test_beste_fassung_steht_vorn():
    """Innerhalb der Gruppe entscheidet der bestehende V1-Score."""
    outs = [
        _result_out("till", _decision("Matrix.720p", imdb="0133093", score=5), _NOW),
        _result_out("till", _decision("Matrix.2160p", imdb="0133093", score=20), _NOW),
    ]
    groups = group_results(outs)
    assert groups[0].releases[0].score == 20


def test_verschiedene_filme_bleiben_getrennt():
    outs = [
        _result_out("till", _decision("Matrix", imdb="0133093"), _NOW),
        _result_out("till", _decision("Inception", imdb="1375666"), _NOW),
    ]
    assert len(group_results(outs)) == 2


def test_ohne_id_wird_nach_titel_gruppiert():
    """Nicht jeder Treffer hat eine ID — dann greift der normalisierte Titel."""
    outs = [
        _result_out("till", _decision("Der.Pate.1972.German.1080p.BluRay-GRP"), _NOW),
        _result_out("till", _decision("Der.Pate.1972.German.2160p.WEB-XYZ"), _NOW),
    ]
    groups = group_results(outs)
    assert len(groups) == 1
    assert len(groups[0].releases) == 2


def test_unterschiedliche_titel_ohne_id_bleiben_getrennt():
    outs = [
        _result_out("till", _decision("Der.Pate.1972.German.1080p"), _NOW),
        _result_out("till", _decision("Highlander.1986.German.1080p"), _NOW),
    ]
    assert len(group_results(outs)) == 2


def test_gruppentitel_bevorzugt_den_sauberen_titel():
    """Radarr zeigt 'Matrix', nicht 'Matrix.1999.German.1080p.BluRay-GRP'."""
    outs = [_result_out("till", _decision("Matrix.1999.German.1080p.BluRay-GRP",
                                          imdb="0133093", year=1999), _NOW)]
    assert group_results(outs)[0].title == "Matrix"


def test_gruppentitel_faellt_auf_release_namen_zurueck():
    outs = [_result_out("till", _decision("Irgendwas.Ohne.Meta.1080p"), _NOW)]
    assert group_results(outs)[0].title


def test_gruppe_uebernimmt_cover_der_ersten_fassung_die_eins_hat():
    outs = [
        _result_out("till", _decision("Matrix.720p", imdb="0133093", score=5), _NOW),
        _result_out("till", _decision("Matrix.2160p", imdb="0133093", score=20,
                                      cover="https://picbit.io/c.webp"), _NOW),
    ]
    assert group_results(outs)[0].cover_url == "https://picbit.io/c.webp"


def test_gruppen_sind_nach_bestem_score_sortiert():
    outs = [
        _result_out("till", _decision("Schwach", imdb="111", score=1), _NOW),
        _result_out("till", _decision("Stark", imdb="222", score=99), _NOW),
    ]
    assert group_results(outs)[0].releases[0].score == 99


def test_leere_liste():
    assert group_results([]) == []
