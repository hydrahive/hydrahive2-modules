"""Studio – REST fürs Hochladen (Spec „Bauplan Etappe 7“, 7a). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import plan, uploads
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}")
Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.post("/uploads")
async def upload_files(project_id: str, auth: Auth, files: Annotated[list[UploadFile], File()]) -> dict:
    guard(auth[0], project_id)
    try:
        return await uploads.save_many(project_id, files)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.post("/plan/elements/{element_id}/references")
async def upload_reference(project_id: str, element_id: str, auth: Auth, files: Annotated[list[UploadFile], File()]) -> dict:
    guard(auth[0], project_id)
    try:
        if len(files) != 1:
            raise plan.PlanError("studio_upload_too_many")
        return await uploads.add_reference(project_id, element_id, files[0])
    except plan.PlanError as e:
        raise coded(e.status, e.code)
