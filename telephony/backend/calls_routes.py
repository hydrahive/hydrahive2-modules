"""API für Anrufe annehmen (PLAN-ANRUFE-2A): Schalter/Ansage, Testanruf, Anrufliste, „Ton gehört?“."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import calls

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


def _no_controls(v: str, *, newlines: bool = True) -> str:
    allowed = "\n\t" if newlines else ""
    if any(ord(ch) < 32 and ch not in allowed for ch in v):
        raise ValueError("enthält Steuerzeichen")
    return v


class CallsIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    answer_calls: bool
    greeting: str = Field("", max_length=500)
    mode: Literal["greeting", "assistant"] | None = None          # None = Assistent-Einstellungen unverändert
    assistant_name: str = Field("", max_length=80)
    assistant_knowledge: str = Field("", max_length=4000)
    assistant_model: str = Field("", max_length=200)

    @field_validator("greeting", "assistant_knowledge")
    @classmethod
    def _clean(cls, v: str) -> str:
        return _no_controls(v)

    @field_validator("assistant_name", "assistant_model")
    @classmethod
    def _clean_line(cls, v: str) -> str:
        return _no_controls(v, newlines=False)


class HeardIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heard: bool


def _fail(e: Exception):
    if isinstance(e, calls.NotFound):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    if isinstance(e, calls.Conflict):
        raise coded(status.HTTP_409_CONFLICT, "not_a_test_call") from None
    raise e


@router.put("/connection/calls")
def put_calls(body: CallsIn, auth: Auth) -> dict:
    try:
        assistant = None if body.mode is None else {
            "mode": body.mode, "assistant_name": body.assistant_name,
            "assistant_knowledge": body.assistant_knowledge, "assistant_model": body.assistant_model}
        calls.update(auth.user_id, body.answer_calls, body.greeting, assistant)
    except Exception as e:  # noqa: BLE001 - _fail ordnet zu
        _fail(e)
    return {"answer_calls": body.answer_calls, "greeting": body.greeting, "mode": body.mode}


@router.post("/connection/test-call")
def test_call(auth: Auth) -> dict:
    try:
        return {"test_until": calls.open_test(auth.user_id), "seconds": calls.TEST_SECONDS}
    except Exception as e:  # noqa: BLE001
        _fail(e)


@router.get("/connection/calls")
def list_calls(auth: Auth) -> dict:
    try:
        return {"calls": calls.list_for(auth.user_id), "unread": calls.unread(auth.user_id)}
    except calls.NotFound:
        return {"calls": [], "unread": 0}


@router.post("/connection/calls/{call_id}/read")
def read(call_id: int, auth: Auth) -> dict:
    try:
        return calls.mark_read(auth.user_id, call_id)
    except Exception as e:  # noqa: BLE001
        _fail(e)


@router.post("/connection/calls/{call_id}/heard")
def heard(call_id: int, body: HeardIn, auth: Auth) -> dict:
    try:
        return calls.confirm(auth.user_id, call_id, body.heard)
    except Exception as e:  # noqa: BLE001
        _fail(e)
