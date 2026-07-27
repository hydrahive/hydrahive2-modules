"""Gruppiert flache Suchtreffer zu Titeln mit mehreren Fassungen.

Der eigentliche Radarr-Effekt: ein Film mit acht Releases ist EINE Karte mit
acht Fassungen, nicht acht Zeilen.

Schluessel in dieser Reihenfolge:
1. imdb/tmdb/tvdb-ID (zuverlaessig)
2. normalisierter sauberer Titel + Jahr
3. aus dem Release-Namen abgeleiteter Titel (Fallback)

Die Freigabe-Logik aus V1 bleibt unberuehrt — hier wird nur umsortiert.
"""
from __future__ import annotations

import re

from .models import ResultGroup, SearchResultOut

# Release-Namen wie "Der.Pate.1972.German.1080p.BluRay.x264-GRP" auf den Titel
# eindampfen: ab dem ersten Qualitaets-/Jahr-Marker wird abgeschnitten.
_RELEASE_NOISE = re.compile(
    r"[.\s_-]+(?:19\d{2}|20\d{2}|german|deutsch|multi|dl|1080p?|2160p?|720p?|uhd|hdr"
    r"|bluray|blu-ray|webrip|web-dl|web|bdrip|dvdrip|remux|x264|x265|h264|h265|hevc"
    r"|av1|aac|ac3|eac3|dts|flac|mp3|complete|s\d{1,3}(?:e\d{1,4})?)\b.*$",
    re.I,
)


def _clean_title(raw: str) -> str:
    cut = _RELEASE_NOISE.sub("", raw)
    cut = cut.replace(".", " ").replace("_", " ")
    return " ".join(cut.split()).strip(" -–,") or raw


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _group_key(result: SearchResultOut) -> tuple[str, str]:
    """(Schluessel, Anzeigetitel)."""
    meta = result.meta
    if meta:
        for identifier in (meta.imdb_id, meta.tmdb_id, meta.tvdb_id):
            if identifier:
                title = meta.title_clean or _clean_title(result.title)
                return f"id:{identifier}", title
        if meta.title_clean:
            suffix = f":{meta.year}" if meta.year else ""
            return f"t:{_normalize(meta.title_clean)}{suffix}", meta.title_clean
    title = _clean_title(result.title)
    return f"t:{_normalize(title)}", title


def group_results(results: list[SearchResultOut]) -> list[ResultGroup]:
    """Fasst Treffer zu Titel-Gruppen zusammen, beste Fassung zuerst."""
    buckets: dict[str, list[SearchResultOut]] = {}
    titles: dict[str, str] = {}
    for result in results:
        key, title = _group_key(result)
        buckets.setdefault(key, []).append(result)
        # Erster gesehener Titel gewinnt — spaetere Fassungen aendern ihn nicht.
        titles.setdefault(key, title)

    groups: list[ResultGroup] = []
    for key, items in buckets.items():
        ordered = sorted(items, key=lambda r: r.score, reverse=True)
        first = _first_meta(ordered)
        groups.append(ResultGroup(
            key=key,
            title=titles[key],
            year=first("year"),
            cover_url=first("cover_url"),
            backdrop_url=first("backdrop_url"),
            rating=first("score"),
            genres=first("genres") or [],
            plot=first("plot"),
            media_type=ordered[0].media_type,
            releases=ordered,
        ))
    groups.sort(key=lambda g: g.releases[0].score, reverse=True)
    return groups


def _first_meta(ordered: list[SearchResultOut]):
    """Erster belegter Metadaten-Wert ueber alle Fassungen hinweg.

    Nicht jede Fassung traegt Cover/Plot — es genuegt, wenn eine es tut.
    """
    def pick(field: str):
        for result in ordered:
            if result.meta is None:
                continue
            value = getattr(result.meta, field, None)
            if value:
                return value
        return None
    return pick
