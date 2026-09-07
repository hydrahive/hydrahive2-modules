from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal, require_principal
from hydrahive.api.middleware.errors import coded

from .models import ExtractRequest, FetchRequest, PolicyUpdate, SearchRequest
from .policy import PolicyError
from .service import OpenTorService

router = APIRouter()
SERVICE = OpenTorService()


def _raise_error(exc: Exception) -> None:
    if isinstance(exc, PolicyError):
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc))
    raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, "opentor_unavailable")


@router.get("/status")
def get_status(principal: Annotated[AuthPrincipal, Depends(require_principal)]) -> dict:
    return SERVICE.status()


@router.get("/policy")
def policy(principal: Annotated[AuthPrincipal, Depends(require_principal)]) -> dict:
    return SERVICE.policy()


@router.put("/policy")
def update_policy(
    body: PolicyUpdate,
    principal: Annotated[AuthPrincipal, Depends(require_admin_principal)],
) -> dict:
    return SERVICE.set_policy(body)


@router.post("/search")
async def search(
    body: SearchRequest,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    try:
        return await SERVICE.search(principal.user_id, None, body)
    except Exception as exc:
        _raise_error(exc)


@router.post("/fetch")
async def fetch(
    body: FetchRequest,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    try:
        return await SERVICE.fetch(principal.user_id, None, body)
    except Exception as exc:
        _raise_error(exc)


@router.post("/extract-iocs")
def extract_iocs(
    body: ExtractRequest,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
) -> dict:
    try:
        return SERVICE.extract_iocs(principal.user_id, body.text)
    except Exception as exc:
        _raise_error(exc)
