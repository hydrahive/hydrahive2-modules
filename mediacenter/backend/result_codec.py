from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import INDEXER_FILE_HOST, INDEXER_HOST
from .models import (
    Decision,
    MediaType,
    ProfileDecision,
    RawRelease,
    ReleaseMeta,
    SelectionStatus,
)

_ALLOWED_REFERENCE_HOSTS = {INDEXER_HOST, INDEXER_FILE_HOST}


class _StoredReleaseMeta(BaseModel):
    """Anzeige-Metadaten in der Ablage.

    Ohne dieses Modell fielen Cover, IMDb-/TVDB-Kennung und Handlung beim
    Speichern still weg (extra="forbid") — die Uebergabe an Radarr/Sonarr
    konnte den Titel danach nicht mehr zuordnen.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    cover_url: str | None = Field(default=None, max_length=2048)
    backdrop_url: str | None = Field(default=None, max_length=2048)
    title_clean: str | None = Field(default=None, max_length=200)
    year: int | None = Field(default=None, ge=1800, le=2100)
    score: float | None = Field(default=None, ge=0, le=10)
    genres: tuple[str, ...] = Field(default=(), max_length=5)
    plot: str | None = Field(default=None, max_length=500)
    imdb_id: str | None = Field(default=None, max_length=32)
    tmdb_id: str | None = Field(default=None, max_length=32)
    tvdb_id: str | None = Field(default=None, max_length=32)
    season: int | None = Field(default=None, ge=0, le=999)
    episode: int | None = Field(default=None, ge=0, le=9999)
    artist: str | None = Field(default=None, max_length=200)
    album: str | None = Field(default=None, max_length=200)
    label: str | None = Field(default=None, max_length=200)

    @field_validator("cover_url", "backdrop_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        """Die Ablage ist eine Vertrauensgrenze: eine manipulierte Datei darf
        keine beliebige Bild-URL ins Frontend schmuggeln."""
        if value is None:
            return None
        from .cover_urls import safe_cover_url
        return safe_cover_url(value)


class _StoredRawRelease(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    title: str = Field(min_length=1, max_length=512)
    guid: str = Field(min_length=1, max_length=512)
    category_id: int = Field(ge=0, le=99_999)
    size_bytes: int | None = Field(default=None, ge=0, le=10**15)
    language: str | None = Field(default=None, max_length=64)
    published_at: datetime | None
    download_url: str | None = Field(default=None, max_length=2048)
    meta: _StoredReleaseMeta | None = None

    @field_validator("download_url")
    @classmethod
    def validate_download_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in _ALLOWED_REFERENCE_HOSTS
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("download_url_invalid")
        return value


class _StoredProfileDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    release: _StoredRawRelease
    media_type: MediaType
    decision: Decision
    reasons: tuple[str, ...] = Field(max_length=64)
    language: str | None = Field(default=None, max_length=64)
    resolution: str | None = Field(default=None, max_length=64)
    format: str | None = Field(default=None, max_length=64)
    bitrate_kbps: int | None = Field(default=None, ge=0, le=10_000_000)
    score: int = Field(ge=-1_000_000, le=1_000_000)
    selection_status: SelectionStatus

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not reason or len(reason) > 256 for reason in value):
            raise ValueError("reasons_invalid")
        return value


def serialize_profile_decision(decision: ProfileDecision) -> str:
    stored = _StoredProfileDecision.model_validate(decision, from_attributes=True)
    return stored.model_dump_json()


def deserialize_profile_decision(payload: str) -> ProfileDecision:
    stored = _StoredProfileDecision.model_validate_json(payload)
    stored_release = stored.release.model_dump()
    stored_meta = stored_release.pop("meta", None)
    release = RawRelease(
        **stored_release,
        meta=ReleaseMeta(**stored_meta) if stored_meta else None,
    )
    return ProfileDecision(
        release=release,
        media_type=stored.media_type,
        decision=stored.decision,
        reasons=stored.reasons,
        language=stored.language,
        resolution=stored.resolution,
        format=stored.format,
        bitrate_kbps=stored.bitrate_kbps,
        score=stored.score,
        selection_status=stored.selection_status,
    )
