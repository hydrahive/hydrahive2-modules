"""API für Anrufe annehmen (PLAN-ANRUFE-2A): Schalter/Ansage, Testanruf, Anrufliste, „Ton gehört?“."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import calls

router = APIRouter()
Auth = Annotated[AuthPrincipal, Depends(require_principal)]


class CallsIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    answer_calls: bool
    greeting: str = Field("", max_length=500)

    @field_validator("greeting")
    @classmethod
    def _clean(cls, v: str) -> str:
        if any(ord(ch) < 32 and ch not in "\n\t" for ch in v):
            raise ValueError("Ansage enthält Steuerzeichen")
        return v


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
        calls.update(auth.user_id, body.answer_calls, body.greeting)
    except Exception as e:  # noqa: BLE001 - _fail ordnet zu
        _fail(e)
    return {"answer_calls": body.answer_calls, "greeting": body.greeting}


@router.post("/connection/test-call")
def test_call(auth: Auth) -> dict:
    try:
        return {"test_until": calls.open_test(auth.user_id), "seconds": calls.TEST_SECONDS}
    except Exception as e:  # noqa: BLE001
        _fail(e)


@router.get("/connection/calls")
def list_calls(auth: Auth) -> dict:
    try:
        return {"calls": calls.list_for(auth.user_id)}
    except calls.NotFound:
        return {"calls": []}


@router.post("/connection/calls/{call_id}/heard")
def heard(call_id: int, body: HeardIn, auth: Auth) -> dict:
    try:
        return calls.confirm(auth.user_id, call_id, body.heard)
    except Exception as e:  # noqa: BLE001
        _fail(e)
