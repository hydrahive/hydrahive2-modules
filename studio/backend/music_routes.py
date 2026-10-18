"""Studio – REST für „Musik erzeugen“ (Spec „Nachtrag 5c-2“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import music, plan
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}/music")
Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.post("", status_code=202)
def make_music(project_id: str, auth: Auth, data: Annotated[Any, Body()] = None) -> dict:
    guard(auth[0], project_id)
    try:
        return music.start(project_id, data)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.get("/defaults")
def music_defaults(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return music.defaults(project_id)
