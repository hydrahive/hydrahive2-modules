"""Zentrale Whitelist der vom Mediaplayer unterstützten Dateiformate."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MediaKind = Literal["audio", "video"]


@dataclass(frozen=True, slots=True)
class MediaFormat:
    kind: MediaKind
    mime: str


MEDIA_FORMATS: dict[str, MediaFormat] = {
    "mp3": MediaFormat("audio", "audio/mpeg"),
    "wav": MediaFormat("audio", "audio/wav"),
    "ogg": MediaFormat("audio", "audio/ogg"),
    "m4a": MediaFormat("audio", "audio/mp4"),
    "flac": MediaFormat("audio", "audio/flac"),
    "mp4": MediaFormat("video", "video/mp4"),
    "webm": MediaFormat("video", "video/webm"),
}


def extension(filename: str | Path) -> str:
    """Liefert eine erlaubte Endung ohne Punkt oder einen Leerstring."""
    suffix = Path(filename).suffix.lower().removeprefix(".")
    return suffix if suffix in MEDIA_FORMATS else ""


def format_for(filename: str | Path) -> MediaFormat | None:
    return MEDIA_FORMATS.get(extension(filename))
