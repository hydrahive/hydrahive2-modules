"""Kopfdaten einer Audiodatei lesen (mutagen, Kern-Abhängigkeit seit #635); fehlende Angaben aus dem Pfad.

Pfad im Plex-Stil: Künstler/Album/NN Titel.ext (auch „NN - Titel“). Nur lesen.
"""
from __future__ import annotations

import re

AUDIO_EXT = {"mp3", "flac", "m4a", "ogg", "opus", "wav", "wma"}
_NUM_TITLE = re.compile(r"^(\d{1,3})\s*(?:[-._]\s*)?(.+)$")
_YEAR = re.compile(r"(\d{4})")


class TagError(Exception):
    pass


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def is_audio(name: str) -> bool:
    return ext_of(name) in AUDIO_EXT


def _first(m, key: str) -> str:
    v = m.get(key) if m is not None else None
    if not v:
        return ""
    return str(v[0] if isinstance(v, list) else v).strip()


def _int(text: str) -> int | None:
    m = re.match(r"\s*(\d+)", text or "")
    return int(m.group(1)) if m else None


def _replaygain(raw) -> float | None:
    if raw is None:
        return None
    for key in ("replaygain_track_gain", "REPLAYGAIN_TRACK_GAIN"):
        try:
            v = raw.get(key) if hasattr(raw, "get") else None
        except Exception:  # noqa: BLE001
            v = None
        if v:
            m = re.match(r"\s*([-+]?\d+(?:\.\d+)?)", str(v[0] if isinstance(v, list) else v))
            if m:
                return float(m.group(1))
    return None


def from_path(rel_path: str) -> dict:
    parts = rel_path.split("/")
    stem = parts[-1].rsplit(".", 1)[0]
    m = _NUM_TITLE.match(stem)
    track_no, title = (int(m.group(1)), m.group(2).strip()) if m else (None, stem)
    artist = parts[0] if len(parts) >= 2 else ""
    album = parts[-2] if len(parts) >= 3 else ""
    return {"artist": artist, "album": album, "title": title, "track_no": track_no}


def read(fileobj, rel_path: str) -> dict:
    """Tags + technische Angaben. TagError, wenn mutagen die Datei nicht als Audio erkennt."""
    import mutagen
    try:
        easy = mutagen.File(fileobj, easy=True)
    except Exception as exc:  # noqa: BLE001 – kaputte Datei
        raise TagError(str(exc)) from None
    if easy is None or getattr(easy, "info", None) is None:
        raise TagError("kein Audio")
    info = easy.info
    guess = from_path(rel_path)
    year = _YEAR.search(_first(easy, "date") or _first(easy, "originaldate") or "")
    out = {
        "artist": _first(easy, "artist") or _first(easy, "albumartist") or guess["artist"],
        "album_artist": _first(easy, "albumartist"),
        "title": _first(easy, "title") or guess["title"],
        "album": _first(easy, "album") or guess["album"],
        "genre": _first(easy, "genre"),
        "year": int(year.group(1)) if year else None,
        "track_no": _int(_first(easy, "tracknumber")) or guess["track_no"],
        "duration_s": round(float(info.length), 3) if getattr(info, "length", None) else None,
        "bitrate": int(info.bitrate) if getattr(info, "bitrate", None) else None,
        "sample_rate": int(info.sample_rate) if getattr(info, "sample_rate", None) else None,
        "format": ext_of(rel_path),
        "replaygain_db": _replaygain(easy),
    }
    return out
