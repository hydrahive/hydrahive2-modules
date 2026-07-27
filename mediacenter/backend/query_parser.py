"""Zerlegt eine natuerlichsprachige Sucheingabe in strukturierte Filter.

Rein lokal und regelbasiert — bewusst KEIN LLM: die Suche muss offline
funktionieren und darf keine Kosten pro Tastendruck erzeugen.

Kernregel: erkannte Teile werden AUS dem Suchbegriff entfernt. Ohne das
scheitert "Matrix von 1999" daran, dass der Indexer nach "von 1999" mitsucht.

Der Parser schlaegt nur vor. Was er erkannt hat, steht in `recognized` und wird
in der Oberflaeche als abnehmbarer Chip gezeigt — keine unsichtbare Magie.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import MediaType

# Jahr nur mit Marker (von/aus/Klammern) — sonst waere "2001 Odyssee im
# Weltraum" kaputt. Reihenfolge: Klammern zuerst, dann Marker.
_YEAR_PATTERNS = (
    re.compile(r"\((?P<year>19\d{2}|20\d{2})\)"),
    re.compile(r"\b(?:von|aus dem jahr|aus|from|year)\s+(?P<year>19\d{2}|20\d{2})\b", re.I),
)
_SXXEYY = re.compile(r"\bS(?P<season>\d{1,3})\s*E(?P<episode>\d{1,4})\b", re.I)
_SEASON_ONLY = re.compile(r"\b(?:staffel|season|s)\s*(?P<season>\d{1,3})\b", re.I)
_EPISODE_ONLY = re.compile(r"\b(?:folge|episode|ep)\s*(?P<episode>\d{1,4})\b", re.I)

_MEDIA_KEYWORDS: tuple[tuple[re.Pattern[str], MediaType], ...] = (
    (re.compile(r"\b(h(ö|oe)rb(u|ü)cher|h(ö|oe)rbuch|audiobook)\b", re.I), "audiobook"),
    (re.compile(r"\b(h(ö|oe)rspiele?|audioplay)\b", re.I), "audioplay"),
    (re.compile(r"\b(e-?books?|ebooks?|buch|b(ü|ue)cher|roman)\b", re.I), "book"),
    (re.compile(r"\b(alben|album|musik|music|song|lied)\b", re.I), "music"),
    (re.compile(r"\b(serien?|series|show|staffel|season)\b", re.I), "tv"),
    (re.compile(r"\b(filme?|movie|kinofilm)\b", re.I), "movie"),
)

_LANGUAGE = re.compile(r"\b(?:auf\s+deutsch|in\s+german|deutsch|german|de)\b", re.I)
_RESOLUTIONS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"\b(?:in\s+)?(?:4k|2160p?|uhd)\b", re.I), 2160),
    (re.compile(r"\b(?:in\s+)?(?:1080p?|full\s*hd|hd)\b", re.I), 1080),
)
_AUDIO_FORMATS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:als\s+)?flac\b", re.I), "flac"),
    (re.compile(r"\b(?:als\s+)?mp3\b", re.I), "mp3"),
)


@dataclass
class ParsedQuery:
    """Ergebnis der Zerlegung. `query` ist der bereinigte Suchbegriff."""
    query: str
    media_type: MediaType | None = None
    year: int | None = None
    season: int | None = None
    episode: str | None = None
    language: str | None = None
    resolution: int | None = None
    audio_format: str | None = None
    recognized: list[str] = field(default_factory=list)


def _cut(text: str, match: re.Match[str]) -> str:
    return text[:match.start()] + " " + text[match.end():]


def parse_query(raw: str) -> ParsedQuery:
    text = " ".join((raw or "").split())
    if not text:
        return ParsedQuery(query="")

    original = text
    result = ParsedQuery(query=text)

    # 1. Jahr
    for pattern in _YEAR_PATTERNS:
        match = pattern.search(text)
        if match:
            result.year = int(match.group("year"))
            result.recognized.append("year")
            text = _cut(text, match)
            break

    # 2. Staffel/Folge — S02E05 zuerst, sonst einzeln
    match = _SXXEYY.search(text)
    if match:
        result.season = int(match.group("season"))
        result.episode = match.group("episode")
        result.media_type = "tv"
        result.recognized += ["season", "episode", "media_type"]
        text = _cut(text, match)
    else:
        match = _SEASON_ONLY.search(text)
        if match:
            result.season = int(match.group("season"))
            result.media_type = "tv"
            result.recognized += ["season", "media_type"]
            text = _cut(text, match)
        match = _EPISODE_ONLY.search(text)
        if match:
            result.episode = match.group("episode")
            result.media_type = "tv"
            if "episode" not in result.recognized:
                result.recognized.append("episode")
            if "media_type" not in result.recognized:
                result.recognized.append("media_type")
            text = _cut(text, match)

    # 3. Medientyp-Schluesselwort (nur wenn noch keiner gesetzt)
    for pattern, media_type in _MEDIA_KEYWORDS:
        match = pattern.search(text)
        if not match:
            continue
        if result.media_type is None:
            result.media_type = media_type
            result.recognized.append("media_type")
        text = _cut(text, match)
        break

    # 4. Sprache
    match = _LANGUAGE.search(text)
    if match:
        result.language = "de"
        result.recognized.append("language")
        text = _cut(text, match)

    # 5. Aufloesung
    for pattern, resolution in _RESOLUTIONS:
        match = pattern.search(text)
        if match:
            result.resolution = resolution
            result.recognized.append("resolution")
            text = _cut(text, match)
            break

    # 6. Audioformat
    for pattern, audio_format in _AUDIO_FORMATS:
        match = pattern.search(text)
        if match:
            result.audio_format = audio_format
            result.recognized.append("audio_format")
            text = _cut(text, match)
            break

    cleaned = " ".join(text.split()).strip(" -–,")
    # Wenn nur Schluesselwoerter drinstanden, waere der Suchbegriff jetzt leer —
    # dann lieber den Originaltext behalten, statt ins Leere zu suchen.
    result.query = cleaned if cleaned else original
    return result
