"""Routen Schriftverkehr + Briefe (Plan L3 Schritt 7), in ``case_routes.router`` eingehängt. Rechte wie dort:
Projektrolle je Fall (``_guard``), kein Fall/kein Mitglied → 404, Rolle zu niedrig → 403. Kein Versand-Endpunkt."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from . import casefile, correspondence, letter_check, letter_templates
from .case_routes import Principal, _call, _guard
from .cases import get_case

router = APIRouter()


class LetterIn(BaseModel):
    letter_type: str = Field("", max_length=40)
    sender: str = Field("", max_length=500)
    recipient: str = Field("", max_length=500)
    date: str = Field("", max_length=10)
    their_ref: str = Field("", max_length=100)
    our_ref: str = Field("", max_length=100)
    subject: str = Field("", max_length=300)
    body: str = Field("", max_length=50000)
    delivery: str = Field("", max_length=40)
    attachments: list[str] = Field(default_factory=list, max_length=30)


class EntryIn(LetterIn):
    direction: str = Field(max_length=3)
    proof: str = Field("", max_length=200)


class EntryPatch(BaseModel):
    letter_type: str | None = Field(None, max_length=40)
    sender: str | None = Field(None, max_length=500)
    recipient: str | None = Field(None, max_length=500)
    date: str | None = Field(None, max_length=10)
    their_ref: str | None = Field(None, max_length=100)
    our_ref: str | None = Field(None, max_length=100)
    subject: str | None = Field(None, max_length=300)
    body: str | None = Field(None, max_length=50000)
    delivery: str | None = Field(None, max_length=40)
    proof: str | None = Field(None, max_length=200)
    attachments: list[str] | None = Field(None, max_length=30)


class SentIn(BaseModel):
    date: str = Field(max_length=10)
    delivery: str = Field(max_length=40)
    proof: str = Field("", max_length=200)


class DraftIn(BaseModel):
    template: str = Field(max_length=40)
    recipient_id: int | None = None


@router.get("/letters/templates")
def templates(_: Principal) -> dict:
    return {"templates": letter_templates.list_templates()}


@router.post("/cases/{pid}/letters/draft")
def draft(pid: str, body: DraftIn, p: Principal) -> dict[str, Any]:
    _guard(p, pid, "read")
    try:
        return letter_templates.draft(body.template, case=get_case(pid) or {}, parties=casefile.list_parties(pid),
                                      recipient_id=body.recipient_id)
    except letter_templates.TemplateError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, f"legal_{e.code}") from None


@router.post("/cases/{pid}/letters/check")
def check(pid: str, body: LetterIn, p: Principal) -> dict[str, Any]:
    _guard(p, pid, "read")
    return letter_check.check(body.model_dump(), case=get_case(pid))


@router.post("/cases/{pid}/correspondence", status_code=status.HTTP_201_CREATED)
def add_entry(pid: str, body: EntryIn, p: Principal) -> dict[str, Any]:
    _guard(p, pid, "write")
    return _call(correspondence.add, pid, body.model_dump(), by=p.username)


@router.patch("/cases/{pid}/correspondence/{entry_id}")
def patch_entry(pid: str, entry_id: int, body: EntryPatch, p: Principal) -> dict[str, Any]:
    _guard(p, pid, "write")
    return _call(correspondence.update, pid, entry_id, body.model_dump(exclude_none=True))


@router.post("/cases/{pid}/correspondence/{entry_id}/sent")
def mark_sent(pid: str, entry_id: int, body: SentIn, p: Principal) -> dict[str, Any]:
    _guard(p, pid, "write")
    return _call(correspondence.mark_sent, pid, entry_id, body.model_dump())


@router.delete("/cases/{pid}/correspondence/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(pid: str, entry_id: int, p: Principal) -> Response:
    _guard(p, pid, "write")
    _call(correspondence.delete, pid, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
