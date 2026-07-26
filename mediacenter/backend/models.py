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
class RawRelease:
    title: str
    guid: str
    category_id: int
    size_bytes: int | None
    language: str | None
    published_at: datetime | None
    download_url: str | None


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


class SearchResponse(BaseModel):
    total: int
    eligible: int
    results: list[SearchResultOut]


class ConnectionTestResponse(BaseModel):
    ok: bool = True
    max_limit: int
    default_limit: int
    search_types: list[str]
    categories: list[int]


class ModuleStatus(BaseModel):
    module: str = "mediacenter"
    state: Literal["ready", "not_configured"]
    indexer_configured: bool
