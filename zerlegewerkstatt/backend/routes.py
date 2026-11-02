"""REST-Routen der Zerlege-Werkstatt."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import store, uploads
from .access import require_project
from .models import CaseIn

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(body: CaseIn, auth: Auth) -> dict:
    require_project(*auth, body.project_id, required="write")
    if not body.authorized:
        raise coded(400, "reverse_authorization_required")
    return store.create_case(auth[0], body)


@router.get("/cases")
def list_cases(
    auth: Auth,
    project_id: Annotated[str, Query(pattern=r"^[A-Za-z0-9-]{8,64}$")],
) -> list[dict]:
    require_project(*auth, project_id)
    return store.list_cases(project_id)


@router.post("/cases/{case_id}/artifacts", status_code=status.HTTP_201_CREATED)
async def upload_artifacts(
    case_id: str,
    auth: Auth,
    files: Annotated[list[UploadFile], File()],
) -> dict:
    case = store.get_case(case_id)
    if not case:
        raise coded(404, "reverse_case_not_found")
    require_project(*auth, case["project_id"], required="write")
    if not files:
        raise coded(400, "reverse_artifact_empty")
    if len(files) > uploads.MAX_FILES_PER_REQUEST:
        raise coded(400, "reverse_artifact_too_many")
    if any(upload.size is None for upload in files):
        raise coded(400, "reverse_artifact_size_unknown")
    if any(upload.size > uploads.MAX_ARTIFACT_BYTES for upload in files):
        raise coded(413, "reverse_artifact_too_large")
    results = []
    for upload in files:
        result = await uploads.store_upload(case_id, upload)
        if result["ok"]:
            try:
                store.add_artifact(case_id, result)
            except Exception:
                uploads.discard_upload(case_id, result)
                raise
        results.append(result)
    return {"files": results}


@router.get("/cases/{case_id}")
def get_case(case_id: str, auth: Auth) -> dict:
    case = store.get_case(case_id)
    if not case:
        raise coded(404, "reverse_case_not_found")
    require_project(*auth, case["project_id"])
    return case
