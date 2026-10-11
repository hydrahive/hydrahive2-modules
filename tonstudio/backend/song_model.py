"""Song-Format ``hydrahive.song`` v1 (SPEC.md §5.1).

Clip- und Spurfelder heißen GENAU wie im Video-Editor (videoeditor/backend/models.py: AudioClip, AudioTrack),
damit das Media-Studio eine Spur durch Kopieren der Felder übernehmen kann (Entscheidung E3). Neu sind nur
``pan`` und ``role``. Alle neuen Felder sind optional, damit alte Songs gültig bleiben.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORMAT = "hydrahive.song"
FORMAT_VERSION = 1

Role = Literal["full", "vocals", "drums", "bass", "other", "fx", "guide"]
SectionKind = Literal["intro", "verse", "prechorus", "chorus", "bridge", "solo", "outro", "other"]


class Clip(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64)
    source_rel: str = Field(min_length=1, max_length=500)
    t_start: float = Field(default=0.0, ge=0)
    src_start: float = Field(default=0.0, ge=0)
    src_end: float = Field(gt=0)
    gain_db: float = Field(default=0.0, ge=-60, le=24)
    fade_in: float = Field(default=0.0, ge=0)
    fade_out: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def _range(self) -> "Clip":
        if self.src_end <= self.src_start:
            raise ValueError("src_end muss nach src_start liegen")
        return self


class Track(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(default="Spur", max_length=120)
    role: Role = "full"
    gain_db: float = Field(default=0.0, ge=-60, le=24)
    pan: float = Field(default=0.0, ge=-1.0, le=1.0)
    mute: bool = False
    solo: bool = False
    clips: list[Clip] = Field(default_factory=list)


class Section(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(default="", max_length=80)
    kind: SectionKind = "other"
    t_start: float = Field(default=0.0, ge=0)
    t_end: float = Field(gt=0)
    lyrics_section: str | None = Field(default=None, max_length=80)


class Ref(BaseModel):
    """Verweis auf Liedtext bzw. Noten (§5.2, §5.4). ``None`` = noch nichts verknüpft."""
    model_config = ConfigDict(extra="allow")
    ref: str | dict | None = None


class Master(BaseModel):
    model_config = ConfigDict(extra="ignore")
    gain_db: float = Field(default=0.0, ge=-60, le=24)
    loudness_lufs: float = Field(default=-14.0, ge=-40, le=0)


class SongIn(BaseModel):
    """Was ein Client schreiben darf. ``id``, ``format``, ``version`` setzt der Server."""
    model_config = ConfigDict(extra="ignore")
    title: str = Field(default="Neuer Song", min_length=1, max_length=200)
    bpm: float | None = Field(default=None, gt=0, le=400)
    key: str | None = Field(default=None, max_length=40)
    time_signature: str = Field(default="4/4", pattern=r"^\d{1,2}/\d{1,2}$")
    sections: list[Section] = Field(default_factory=list, max_length=200)
    tracks: list[Track] = Field(default_factory=list, max_length=64)
    master: Master = Field(default_factory=Master)
    lyrics: Ref = Field(default_factory=Ref)
    score: Ref = Field(default_factory=Ref)
