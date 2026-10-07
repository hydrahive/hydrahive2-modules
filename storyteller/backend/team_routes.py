"""Buch als eigenes Projekt mit Schreib-Team anlegen (Spec schreib-team.md §4, Plan T1c).

Rechte: ``module.storyteller`` (Grundfreigabe; im Betrieb prüft sie zusätzlich das Modul-Tor des Kerns) UND
``storyteller.create_project`` (Projekte anlegen ist sonst Admin-Sache). Admins dürfen immer. Der Nutzer wird
Ersteller und damit Admin des neuen Projekts.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.access import check
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from ._route_base import _call
from .team import setup

CREATE_CAP = "storyteller.create_project"
Principal = Annotated[AuthPrincipal, Depends(require_principal)]
router = APIRouter()


class BookProjectIn(BaseModel):
    title: str = Field(max_length=200)
    kind: str = Field(max_length=20)
    language: str = Field(default="de", max_length=5)
    audience: str = Field(default="", max_length=200)
    idea: str = Field(default="", max_length=2000)
    model: str = Field(default="", max_length=200)


def _may_create(p: AuthPrincipal) -> bool:
    return all(check.can_use(user_id=p.user_id, role=p.role, capability=c)
               for c in ("module.storyteller", CREATE_CAP))


@router.get("/book-projects/can-create")
def can_create(principal: Principal):
    return {"can_create": _may_create(principal)}


@router.post("/book-projects")
def create_book_project(body: BookProjectIn, principal: Principal):
    if not _may_create(principal):
        raise coded(status.HTTP_403_FORBIDDEN, "capability_denied", capability=CREATE_CAP)
    fields = body.model_dump(exclude={"model"})
    return _call(setup.create_book_project, principal.username, fields, model=body.model)
