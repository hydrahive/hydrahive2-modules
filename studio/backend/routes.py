"""Studio – REST unter /api/modules/studio (studio/SPEC.md).

Alle Projekt-Routen prüfen Mitgliedschaft (fremdes oder unbekanntes Projekt → 404). Dateien liefert der Kern über
/api/files aus (mit Range und Rechteprüfung) – das Modul hat keinen eigenen Datei-Endpunkt.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.projects._config_io import list_for_user

from . import library, overview, plan, render, voice_provider, waveform
from ._guard import guard
from .draft_routes import router as draft_router
from .music_routes import router as music_router
from .plan_routes import router as plan_router
from .shot_routes import router as shot_router
from .subtitle_routes import router as subtitle_router
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


@router.post("/projects/{project_id}/render", status_code=202)
def post_render(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    try:
        return render.start(project_id)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.get("/projects/{project_id}/renders")
def get_renders(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return render.list_renders(project_id)


@router.get("/projects/{project_id}/waveform")
async def get_waveform(project_id: str, rel: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    try:
        return await asyncio.to_thread(waveform.waveform, project_id, rel)
    except waveform.NotFound:
        raise coded(404, "studio_media_not_found")


@router.get("/projects/{project_id}/voices")
async def get_voices(project_id: str, auth: Auth, model: str = "") -> dict:
    """Stimmen des Sprachmodells (Auswahl im Shot); ohne `model` das des Drehbuchs bzw. der Standard des Servers."""
    guard(auth[0], project_id)
    m = model.strip()[:200] or plan.get_head(project_id)["models"]["voice"] or voice_provider.server_default_model()
    return {"model": m, "voices": await asyncio.to_thread(voice_provider.voices, m)}


@router.get("/projects/{project_id}/overview")
def get_overview(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return overview.overview(project_id)


router.include_router(draft_router)
router.include_router(music_router)
router.include_router(plan_router)
router.include_router(shot_router)
router.include_router(subtitle_router)
router.include_router(timeline_router)
