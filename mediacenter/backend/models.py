from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MediaType = Literal["movie", "tv", "book", "audiobook", "audioplay", "music"]


@dataclass(frozen=True)
class IndexerCapabilities:
    max_limit: int
    default_limit: int
    search_types: set[str]
    categories: set[int]
    supported_params: dict[str, set[str]] = field(default_factory=dict)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=200)
    media_type: MediaType
    limit: int = Field(default=50, ge=1, le=100)
    year: int | None = Field(default=None, ge=1800, le=2100)
    season: int | None = Field(default=None, ge=0, le=999)
    episode: str | None = Field(default=None, min_length=1, max_length=16)
    author: str | None = Field(default=None, min_length=1, max_length=200)
    artist: str | None = Field(default=None, min_length=1, max_length=200)
    album: str | None = Field(default=None, min_length=1, max_length=200)
    max_age_days: int | None = Field(default=None, ge=1, le=3650)
    min_size_mb: int | None = Field(default=None, ge=0, le=1_000_000)
    max_size_mb: int | None = Field(default=None, ge=0, le=1_000_000)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("query_too_short")
        return normalized

    @model_validator(mode="after")
    def validate_ranges(self) -> "SearchRequest":
        if (
            self.min_size_mb is not None
            and self.max_size_mb is not None
            and self.min_size_mb > self.max_size_mb
        ):
            raise ValueError("size_range_invalid")
        media_filters = {
            "season": {"tv"},
            "episode": {"tv"},
            "author": {"book"},
            "artist": {"music"},
            "album": {"music"},
        }
        for name, media_types in media_filters.items():
            if getattr(self, name) is not None and self.media_type not in media_types:
                raise ValueError("filter_not_allowed_for_media_type")
        return self


@dataclass(frozen=True)
class ReleaseMeta:
    """Anzeige-Metadaten aus den Newznab-Attributen (Cover, Bewertung, Handlung).

    Alle Felder optional: fehlt alles, bleibt `RawRelease.meta` None und die
    Oberflaeche verhaelt sich wie in V1. Werte werden nie geraten — was der
    Indexer nicht liefert oder was unplausibel ist, bleibt None.
    """
    cover_url: str | None = None
    backdrop_url: str | None = None
    title_clean: str | None = None   # imdbtitle/tvtitle — echter Titel statt Release-Name
    year: int | None = None
    score: float | None = None       # 0..10
    genres: tuple[str, ...] = ()
    plot: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    tvdb_id: str | None = None
    season: int | None = None
    episode: int | None = None
    artist: str | None = None
    album: str | None = None
    label: str | None = None

    def text_values(self) -> tuple[str, ...]:
        """Alle Freitext-/URL-Werte — Grundlage der Secret-Pruefung.

        Wird von `redaction.release_contains_secret` genutzt. Neue Textfelder
        MUESSEN hier auftauchen, sonst entsteht ein Leak-Pfad.
        """
        return tuple(
            value for value in (
                self.cover_url, self.backdrop_url, self.title_clean, self.plot,
                self.imdb_id, self.tmdb_id, self.tvdb_id,
                self.artist, self.album, self.label, *self.genres,
            ) if value
        )


@dataclass(frozen=True)
class RawRelease:
    title: str
    guid: str
    category_id: int
    size_bytes: int | None
    language: str | None
    published_at: datetime | None
    download_url: str | None
    meta: ReleaseMeta | None = None


Decision = Literal["eligible", "rejected"]
SelectionStatus = Literal[
    "ready", "quality_preference_required", "format_preference_required"
]


@dataclass(frozen=True)
class ProfileDecision:
    release: RawRelease
    media_type: MediaType
    decision: Decision
    reasons: tuple[str, ...]
    language: str | None
    resolution: str | None
    format: str | None
    bitrate_kbps: int | None
    score: int
    selection_status: SelectionStatus = "ready"


class ReleaseMetaOut(BaseModel):
    """Anzeige-Metadaten in der API-Antwort. Alle Felder optional."""
    cover_url: str | None = None
    backdrop_url: str | None = None
    title_clean: str | None = None
    year: int | None = None
    score: float | None = None
    genres: list[str] = []
    plot: str | None = None
    imdb_id: str | None = None
    tmdb_id: str | None = None
    tvdb_id: str | None = None
    season: int | None = None
    episode: int | None = None
    artist: str | None = None
    album: str | None = None
    label: str | None = None

    @classmethod
    def from_meta(cls, meta: "ReleaseMeta | None") -> "ReleaseMetaOut | None":
        if meta is None:
            return None
        return cls(
            cover_url=meta.cover_url, backdrop_url=meta.backdrop_url,
            title_clean=meta.title_clean, year=meta.year, score=meta.score,
            genres=list(meta.genres), plot=meta.plot, imdb_id=meta.imdb_id,
            tmdb_id=meta.tmdb_id, tvdb_id=meta.tvdb_id, season=meta.season,
            episode=meta.episode, artist=meta.artist, album=meta.album,
            label=meta.label,
        )


class SearchResultOut(BaseModel):
    result_id: str | None
    title: str
    media_type: MediaType
    category_id: int
    size_bytes: int | None
    age_days: int | None
    decision: Decision
    reasons: list[str]
    language: str | None
    resolution: str | None
    format: str | None
    bitrate_kbps: int | None
    score: int
    selection_status: SelectionStatus
    meta: ReleaseMetaOut | None = None


class ResultGroup(BaseModel):
    """Ein Titel mit allen gefundenen Fassungen — die Karte im Poster-Raster."""
    key: str
    title: str
    year: int | None = None
    cover_url: str | None = None
    backdrop_url: str | None = None
    rating: float | None = None
    genres: list[str] = []
    plot: str | None = None
    media_type: MediaType
    releases: list[SearchResultOut]


class InterpretedQuery(BaseModel):
    """Was der Parser aus der freien Eingabe gelesen hat.

    Die Oberflaeche zeigt das als abnehmbare Chips — der Nutzer sieht die
    Interpretation, statt sie erraten zu muessen.
    """
    query: str
    recognized: list[str] = []
    year: int | None = None
    season: int | None = None
    episode: str | None = None
    language: str | None = None
    resolution: int | None = None
    audio_format: str | None = None


class SearchResponse(BaseModel):
    total: int
    eligible: int
    results: list[SearchResultOut]
    groups: list[ResultGroup] = []
    interpreted: InterpretedQuery | None = None


class ConnectionTestResponse(BaseModel):
    ok: bool = True
    max_limit: int
    default_limit: int
    search_types: list[str]
    categories: list[int]
    sab_version: str | None = None
    sab_categories: list[str] = Field(default_factory=list)


class EnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: str = Field(min_length=20, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    priority: Literal["default", "high", "low"] = "default"


class JobOut(BaseModel):
    result_id: str
    title: str
    media_type: MediaType
    state: str
    sab_job_id: str | None
    status: str
    progress: float | None
    eta: str | None
    speed_kbps: float | None
    error_code: str | None
    updated_at: str


class EnqueueResponse(BaseModel):
    result_id: str
    title: str
    media_type: MediaType
    state: str
    sab_job_id: str | None
    error_code: str | None


class ModuleStatus(BaseModel):
    module: str = "mediacenter"
    state: Literal["ready", "not_configured"]
    indexer_configured: bool
    sab_configured: bool = False
