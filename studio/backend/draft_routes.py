"""Studio – REST für Drehbuch-Entwürfe (Spec „Bauplan B2“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import draft_apply, draft_book, draft_idea, plan
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}/plan/draft")
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Data = Annotated[dict[str, Any], Body()]


@router.post("/idea")
async def post_idea(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    try:
        return await draft_idea.draft(project_id, data)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.get("/books")
def get_books(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return draft_book.list_books(project_id)


@router.post("/book")
def post_book(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    try:
        return draft_book.draft(project_id, data)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.post("/apply")
def post_apply(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    try:
        return draft_apply.apply(project_id, data.get("draft"))
    except plan.PlanError as e:
        raise coded(e.status, e.code)
