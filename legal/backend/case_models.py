"""Eingabemodelle der Fall-Routen (case_routes.py). Grenzen wie in cases.py / casefile.py; die Fachprüfung macht dort."""
from __future__ import annotations

from pydantic import BaseModel, Field


class CaseIn(BaseModel):
    title: str = Field(max_length=200)
    area: str = Field("", max_length=100)
    state: str = Field(max_length=4)
    summary: str = Field("", max_length=2000)
    facts: str = Field("", max_length=20000)
    goal: str = Field("", max_length=2000)
    our_ref: str = Field("", max_length=100)
    their_ref: str = Field("", max_length=100)
    model: str = Field("", max_length=200)


class CasePatch(BaseModel):
    title: str | None = Field(None, max_length=200)
    area: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=4)
    status: str | None = Field(None, max_length=20)
    summary: str | None = Field(None, max_length=2000)
    facts: str | None = Field(None, max_length=20000)
    goal: str | None = Field(None, max_length=2000)
    our_ref: str | None = Field(None, max_length=100)
    their_ref: str | None = Field(None, max_length=100)


class PartyIn(BaseModel):
    role: str = Field(max_length=20)
    name: str = Field(max_length=200)
    address: str = Field("", max_length=500)
    contact: str = Field("", max_length=300)
    note: str = Field("", max_length=2000)


class DeadlineIn(BaseModel):
    label: str = Field(max_length=200)
    event_date: str = Field(max_length=10)
    kind: str = Field(max_length=10)
    amount: int = Field(ge=0, le=3660)
    start_rule: str = Field("event", max_length=10)
    note: str = Field("", max_length=2000)


class CalcIn(BaseModel):
    event_date: str = Field(max_length=10)
    kind: str = Field(max_length=10)
    amount: int = Field(ge=0, le=3660)
    start_rule: str = Field("event", max_length=10)
    state: str = Field(max_length=4)


class StatusIn(BaseModel):
    status: str = Field(max_length=10)


class NoteIn(BaseModel):
    title: str = Field(max_length=200)
    body: str = Field(max_length=20000)
    citations: list[str] = Field(default_factory=list, max_length=20)
