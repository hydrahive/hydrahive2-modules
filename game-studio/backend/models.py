"""Strict request models for the early Game Studio vertical slice."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DraftCreate(StrictModel):
    entry_kind: Literal["new", "adopt", "archive"]
    title: str = Field(min_length=1, max_length=120)
    idea: str = Field(default="", max_length=4000)
    genre: str = Field(default="", max_length=120)
    target_platform: Literal["desktop", "web", "mobile"] = "desktop"

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped


class DraftUpdate(StrictModel):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    idea: str | None = Field(default=None, max_length=4000)
    genre: str | None = Field(default=None, max_length=120)
    target_platform: Literal["desktop", "web", "mobile"] | None = None
    core_action: str | None = Field(default=None, max_length=2000)
    success_condition: str | None = Field(default=None, max_length=2000)
    current_step: int | None = Field(default=None, ge=1, le=4)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped
