"""Pydantic contracts and controlled values for the tickets domain."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


TicketStatus = Literal[
    "open", "triaged", "in_progress", "waiting", "resolved", "closed", "cancelled"
]
TicketPriority = Literal["low", "normal", "high", "urgent"]
ActorKind = Literal["user", "agent", "system"]


class TicketCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=20_000)
    priority: TicketPriority = "normal"
    category: str = Field(default="", max_length=80)
    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(
        default_factory=list, max_length=20
    )
    assigned_to: str | None = Field(default=None, max_length=128)
    team_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    due_at: str | None = Field(default=None, max_length=64)

    @field_validator("title", "category", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator("title")
    @classmethod
    def non_blank_title(cls, value: str) -> str:
        if not value:
            raise ValueError("title must not be blank")
        return value


class TicketUpdate(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=20_000)
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: str | None = Field(default=None, max_length=80)
    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] | None = Field(
        default=None, max_length=20
    )
    assigned_to: str | None = Field(default=None, max_length=128)
    team_id: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)
    session_id: str | None = Field(default=None, max_length=128)
    due_at: str | None = Field(default=None, max_length=64)

    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def strip_update_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("title")
    @classmethod
    def non_blank_update_title(cls, value: str | None) -> str | None:
        if value == "":
            raise ValueError("title must not be blank")
        return value


class TicketCommentCreate(StrictModel):
    body: str = Field(min_length=1, max_length=20_000)

    @field_validator("body")
    @classmethod
    def non_blank_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("body must not be blank")
        return value


class TicketListQuery(StrictModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    team_id: str | None = None
    assigned_to: str | None = None
    project_id: str | None = None
    query: str | None = Field(default=None, max_length=200)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SavedViewCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    filters: dict[str, object] = Field(default_factory=dict)
    sort: Literal["updated_at", "due_at", "created_at", "priority", "number"] = "updated_at"
    direction: Literal["asc", "desc"] = "desc"
    team_id: str | None = Field(default=None, max_length=64)


class BulkUpdateRequest(StrictModel):
    ticket_ids: list[str] = Field(min_length=1, max_length=100)
    update: TicketUpdate


class TeamCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2_000)

    @field_validator("name", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def non_blank_name(cls, value: str) -> str:
        if not value:
            raise ValueError("name must not be blank")
        return value


class TeamUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("name", "description")
    @classmethod
    def strip_update_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class TeamMemberUpsert(StrictModel):
    user_id: str = Field(min_length=1, max_length=128)
    role: Literal["member", "lead"] = "member"
