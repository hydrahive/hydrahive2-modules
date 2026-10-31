"""Eingaben der Programm-Schnittstellen (program_routes.py, program_routes_lists.py)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NameIn(_In):
    name: str = Field(max_length=200)


class PlaylistIn(_In):
    name: str | None = Field(default=None, max_length=200)
    order_mode: str | None = None
    at_end: str | None = None


class ItemsIn(_In):
    track_ids: list[str] = Field(max_length=500)


class MoveIn(_In):
    from_: int = Field(alias="from")
    to: int


class SearchIn(_In):
    q: str = Field(default="", max_length=200)
    artist: str = Field(default="", max_length=300)
    genre: str = Field(default="", max_length=100)
    format: str = Field(default="", max_length=10)
    year_from: int | None = Field(default=None, ge=0, le=3000)
    year_to: int | None = Field(default=None, ge=0, le=3000)


class MixIn(_In):
    name: str = Field(max_length=200)
    rules: dict
    allow_long: bool = False


class PreviewIn(_In):
    rules: dict
    allow_long: bool = False


class ProgramIn(_In):
    mode: Literal["all", "playlist", "mix"]
    ref_id: str = Field(default="", max_length=40)


class QueueIn(_In):
    track_id: str = Field(max_length=40)
    front: bool = False


class PosIn(_In):
    pos: int


class ExcludeIn(_In):
    rules: dict
    allow_long: bool = False
