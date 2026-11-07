"""Strict workspace-backed Game Studio project models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Engine = Literal["godot", "unreal", "unity"]
EntryKind = Literal["new", "adopt", "archive"]
Platform = Literal["desktop", "web", "mobile"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProjectCreate(StrictModel):
    entry_kind: EntryKind
    engine: Engine
    engine_version: str = Field(default="auto", min_length=1, max_length=32, pattern=r"^(?:auto|\d+\.\d+(?:\.\d+)?)$")
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

    @model_validator(mode="after")
    def _version_matches_engine(self) -> "ProjectCreate":
        if self.engine != "unreal" and self.engine_version != "auto":
            raise ValueError("engine_version is only supported for Unreal Engine")
        return self


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


class ProjectGenerate(StrictModel):
    revision: int = Field(ge=1)


class EngineRun(StrictModel):
    schema_version: Literal[1] = 1
    kind: Literal["unreal-build", "unreal-test"]
    status: Literal["passed", "failed"]
    exit_code: int = Field(ge=0, le=255)
    finished_at: str = Field(min_length=20, max_length=32, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    log_path: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def _result_is_consistent(self) -> "EngineRun":
        if (self.status == "passed") != (self.exit_code == 0):
            raise ValueError("run status and exit code disagree")
        if self.log_path.startswith("/") or ".." in self.log_path.split("/"):
            raise ValueError("log_path must stay inside the workspace")
        return self


class WorkspaceProject(StrictModel):
    schema_version: Literal[1] = 1
    project_id: str = Field(min_length=1, max_length=128)
    entry_kind: EntryKind
    engine: Engine
    engine_version: str = Field(default="auto", min_length=1, max_length=32, pattern=r"^(?:auto|\d+\.\d+(?:\.\d+)?)$")
    engine_project_name: str = Field(default="", max_length=64, pattern=r"^(?:|[A-Za-z][A-Za-z0-9]{0,63})$")
    engine_project_path: str = Field(default="", max_length=512)
    engine_project_ready: bool = False
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

    @model_validator(mode="after")
    def _engine_project_is_consistent(self) -> "WorkspaceProject":
        if self.engine != "unreal" and self.engine_version != "auto":
            raise ValueError("engine_version is only supported for Unreal Engine")
        if self.engine_project_path and (self.engine_project_path.startswith("/") or ".." in self.engine_project_path.split("/")):
            raise ValueError("engine_project_path must stay inside the workspace")
        if self.engine_project_ready and not (self.engine_project_name and self.engine_project_path):
            raise ValueError("ready engine project requires name and path")
        return self
