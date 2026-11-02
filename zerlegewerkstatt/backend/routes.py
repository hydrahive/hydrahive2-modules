"""REST-Routen der Zerlege-Werkstatt."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import store
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


@router.get("/cases/{case_id}")
def get_case(case_id: str, auth: Auth) -> dict:
    case = store.get_case(case_id)
    if not case:
        raise coded(404, "reverse_case_not_found")
    require_project(*auth, case["project_id"])
    return case
