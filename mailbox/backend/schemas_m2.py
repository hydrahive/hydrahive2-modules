"""Eingabe-Schemas M2 (Entwürfe, Aktionen). Längen begrenzt; Inhalte prüft drafts.py/actions.py zusätzlich."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DraftIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str = Field(max_length=64)
    to: str = Field(default="", max_length=10_000)
    cc: str = Field(default="", max_length=10_000)
    bcc: str = Field(default="", max_length=10_000)
    subject: str = Field(default="", max_length=998)
    body: str = Field(default="", max_length=1_000_000)
    mode: Literal["new", "reply", "reply_all", "forward"] = "new"
    ref_message: int | None = None
    with_attachments: bool = False


class ActionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[int] = Field(min_length=1, max_length=500)
    action: Literal["seen", "unseen", "flag", "unflag", "move", "delete"]
    target: str | None = Field(default=None, max_length=500)
