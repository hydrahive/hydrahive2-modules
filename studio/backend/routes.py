"""Studio – REST unter /api/modules/studio (studio/SPEC.md).

Alle Projekt-Routen prüfen Mitgliedschaft (fremdes oder unbekanntes Projekt → 404). Dateien liefert der Kern über
/api/files aus (mit Range und Rechteprüfung) – das Modul hat keinen eigenen Datei-Endpunkt.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.projects._config_io import list_for_user

from . import library, overview
from ._guard import guard
from .plan_routes import router as plan_router
from .shot_routes import router as shot_router
from .timeline_routes import router as timeline_router

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/projects")
def list_projects(auth: Auth) -> dict:
    return {"projects": [{"id": p["id"], "name": p.get("name") or p["id"]} for p in list_for_user(auth[0])]}


@router.get("/projects/{project_id}/library")
async def get_library(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return await asyncio.to_thread(library.list_items, project_id)


@router.get("/projects/{project_id}/overview")
def get_overview(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return overview.overview(project_id)


router.include_router(plan_router)
router.include_router(shot_router)
router.include_router(timeline_router)
