"""Baut ReleaseMeta aus den Newznab-Attributen eines Items.

Der Indexer liefert (live verifiziert 27.07.2026) je nach Medientyp coverurl,
backdropurl, imdb/tmdb/tvdbid, imdbtitle/tvtitle, imdbyear, imdbscore, imdbplot,
genre, season/episode, artist/album/label. V1 hat all das verworfen.

Grundsatz: streng und still. Unplausible Werte werden verworfen statt geraten,
und ein kaputtes Attribut darf niemals die Suche scheitern lassen.
"""
from __future__ import annotations

from .cover_urls import safe_cover_url
from .models import ReleaseMeta

MAX_PLOT_LENGTH = 500
MAX_TITLE_LENGTH = 200
MAX_GENRES = 5
MAX_GENRE_LENGTH = 40
MAX_NAME_LENGTH = 200
MAX_ID_LENGTH = 32


def _text(attrs: dict[str, str], key: str, limit: int) -> str | None:
    value = (attrs.get(key) or "").strip()
    if not value:
        return None
    return value[:limit]


def _identifier(attrs: dict[str, str], key: str) -> str | None:
    """IDs sind rein alphanumerisch — alles andere ist verdaechtig."""
    value = (attrs.get(key) or "").strip()
    if not value or len(value) > MAX_ID_LENGTH or not value.replace("tt", "").isalnum():
        return None
    return value


def _int(attrs: dict[str, str], key: str, low: int, high: int) -> int | None:
    try:
        parsed = int((attrs.get(key) or "").strip())
    except (TypeError, ValueError):
        return None
    return parsed if low <= parsed <= high else None


def _score(attrs: dict[str, str]) -> float | None:
    try:
        parsed = float((attrs.get("imdbscore") or "").strip())
    except (TypeError, ValueError):
        return None
    return round(parsed, 1) if 0.0 <= parsed <= 10.0 else None


def _genres(attrs: dict[str, str]) -> tuple[str, ...]:
    raw = (attrs.get("genre") or "").strip()
    if not raw:
        return ()
    parts = [p.strip()[:MAX_GENRE_LENGTH] for p in raw.split(",")]
    return tuple(p for p in parts if p)[:MAX_GENRES]


def build_meta(attrs: dict[str, str]) -> ReleaseMeta | None:
    """Erzeugt ReleaseMeta oder None, wenn kein einziges Feld belegt ist."""
    meta = ReleaseMeta(
        cover_url=safe_cover_url(attrs.get("coverurl")),
        backdrop_url=safe_cover_url(attrs.get("backdropurl")),
        title_clean=_text(attrs, "imdbtitle", MAX_TITLE_LENGTH)
        or _text(attrs, "tvtitle", MAX_TITLE_LENGTH),
        year=_int(attrs, "imdbyear", 1800, 2100),
        score=_score(attrs),
        genres=_genres(attrs),
        plot=_text(attrs, "imdbplot", MAX_PLOT_LENGTH),
        imdb_id=_identifier(attrs, "imdb"),
        tmdb_id=_identifier(attrs, "tmdb"),
        tvdb_id=_identifier(attrs, "tvdbid"),
        season=_int(attrs, "season", 0, 999),
        episode=_int(attrs, "episode", 0, 9999),
        artist=_text(attrs, "artist", MAX_NAME_LENGTH),
        album=_text(attrs, "album", MAX_NAME_LENGTH),
        label=_text(attrs, "label", MAX_NAME_LENGTH),
    )
    if meta == ReleaseMeta():
        return None
    return meta
