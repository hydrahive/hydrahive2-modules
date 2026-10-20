"""Routen Fälle/Fallakte/Fristenrechner (Plan L2 Schritt 4); in ``routes.router`` eingehängt.

Kern-Tor davor: Freigabe ``module.legal`` + Vault-PIN. Anlegen braucht zusätzlich ``legal.create_case``. Jede
``/cases/{pid}``-Route prüft die Projektrolle (``access.case_access``): kein Fall/kein Mitglied → 404, Rolle zu
niedrig → 403. IDs von Beteiligten/Fristen/Notizen/Vorschlägen gelten nur zusammen mit ihrem Fall.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from . import casefile, cases
from .access import case_access
from .holidays_de import STATES

try:
    from hydrahive.access.deps import require_capability
    _create_dep = require_capability("legal.create_case")
except ImportError:  # Kern ohne Freigaben-System → nur Admins
    from hydrahive.api.middleware.auth import require_admin as _create_dep  # type: ignore[assignment]

router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]
Creator = Annotated[Any, Depends(_create_dep)]


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


def _err(e: cases.CaseError):
    return coded(e.status, f"legal_{e.code}", **e.params)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except cases.CaseError as e:
        raise _err(e) from None


def _guard(p: AuthPrincipal, pid: str, need: str) -> None:
    result = case_access(p.username, p.role, pid, need)
    if result == "missing":
        raise coded(status.HTTP_404_NOT_FOUND, "legal_case_not_found")
    if result == "read_only":
        raise coded(status.HTTP_403_FORBIDDEN, "legal_case_read_only")


@router.get("/states")
def states(_: Principal) -> dict:
    return {"states": STATES}


@router.post("/deadline/calc")
def deadline_calc(body: CalcIn, _: Principal) -> dict:
    return _call(casefile.calc, body.model_dump(), body.state.upper())


@router.get("/cases")
def list_cases(p: Principal) -> dict:
    items = cases.list_cases(p.username, p.role)
    for item in items:
        nxt = next((d for d in casefile.list_deadlines(item["project_id"]) if d["status"] == "open"), None)
        item["next_deadline"] = {"label": nxt["label"], "due_date": nxt["due_date"]} if nxt else None
    return {"cases": items}


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(body: CaseIn, principal: Creator) -> dict:
    data = body.model_dump()
    model = data.pop("model")
    return _call(cases.create_case, principal.username, data, model=model)


@router.get("/cases/{pid}")
def get_case(pid: str, p: Principal) -> dict:
    _guard(p, pid, "read")
    from hydrahive.projects import _members_model
    from hydrahive.projects._config_io import get as get_project
    role = "admin" if p.role == "admin" else _members_model.role_of(get_project(pid) or {}, p.username)
    return {**_call(casefile.snapshot, pid), "role": role}


@router.patch("/cases/{pid}")
def patch_case(pid: str, body: CasePatch, p: Principal) -> dict:
    _guard(p, pid, "write")
    return _call(cases.update_case, pid, body.model_dump(exclude_none=True))


@router.post("/cases/{pid}/parties", status_code=status.HTTP_201_CREATED)
def add_party(pid: str, body: PartyIn, p: Principal) -> dict:
    _guard(p, pid, "write")
    return _call(casefile.add_party, pid, body.model_dump())


@router.delete("/cases/{pid}/parties/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_party(pid: str, party_id: int, p: Principal) -> Response:
    _guard(p, pid, "write")
    _call(casefile.delete_party, pid, party_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cases/{pid}/deadlines", status_code=status.HTTP_201_CREATED)
def add_deadline(pid: str, body: DeadlineIn, p: Principal) -> dict:
    _guard(p, pid, "write")
    return _call(casefile.add_deadline, pid, body.model_dump())


@router.patch("/cases/{pid}/deadlines/{deadline_id}")
def set_deadline_status(pid: str, deadline_id: int, body: StatusIn, p: Principal) -> dict:
    _guard(p, pid, "write")
    _call(casefile.set_deadline_status, pid, deadline_id, body.status)
    return {"id": deadline_id, "status": body.status}


@router.delete("/cases/{pid}/deadlines/{deadline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deadline(pid: str, deadline_id: int, p: Principal) -> Response:
    _guard(p, pid, "write")
    _call(casefile.delete_deadline, pid, deadline_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cases/{pid}/notes", status_code=status.HTTP_201_CREATED)
def add_note(pid: str, body: NoteIn, p: Principal) -> dict:
    _guard(p, pid, "write")
    return _call(casefile.add_note, pid, author="user", author_name=p.username, title=body.title, body=body.body,
                 citations=body.citations)


@router.delete("/cases/{pid}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(pid: str, note_id: int, p: Principal) -> Response:
    _guard(p, pid, "write")
    _call(casefile.delete_note, pid, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/cases/{pid}/proposals")
def proposals(pid: str, p: Principal) -> dict:
    _guard(p, pid, "read")
    return {"proposals": casefile.list_proposals(pid)}


@router.post("/cases/{pid}/proposals/{proposal_id}/{action}")
def decide(pid: str, proposal_id: int, action: str, p: Principal) -> dict:
    if action not in ("accept", "reject"):
        raise coded(status.HTTP_404_NOT_FOUND, "legal_action_unknown")
    _guard(p, pid, "write")
    return _call(casefile.decide, pid, proposal_id, accept=action == "accept", by=p.username)
