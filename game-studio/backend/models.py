"""Strict workspace-backed Game Studio project models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Engine = Literal["godot", "unreal", "unity"]
EntryKind = Literal["new", "adopt", "archive"]
Platform = Literal["desktop", "web", "mobile"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProjectCreate(StrictModel):
    entry_kind: EntryKind
    engine: Engine
    title: str = Field(min_length=1, max_length=120)
    idea: str = Field(default="", max_length=4000)
    genre: str = Field(default="", max_length=120)
    target_platform: Platform = "desktop"

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        return stripped


class ProjectUpdate(StrictModel):
    revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    idea: str | None = Field(default=None, max_length=4000)
    genre: str | None = Field(default=None, max_length=120)
    target_platform: Platform | None = None
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


class WorkspaceProject(StrictModel):
    schema_version: Literal[1] = 1
    project_id: str = Field(min_length=1, max_length=128)
    entry_kind: EntryKind
    engine: Engine
    title: str = Field(min_length=1, max_length=120)
    idea: str = Field(default="", max_length=4000)
    genre: str = Field(default="", max_length=120)
    target_platform: Platform = "desktop"
    core_action: str = Field(default="", max_length=2000)
    success_condition: str = Field(default="", max_length=2000)
    current_step: int = Field(default=1, ge=1, le=4)
    revision: int = Field(default=1, ge=1)
    created_at: str
    updated_at: str
