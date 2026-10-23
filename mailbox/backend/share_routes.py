"""Freigaben eines Kontos für Agenten (PLAN-M3a) – nur der Besitzer. Fremdes Konto = 404, ungültiges Ziel = 422."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import accounts, agent_audit, shares

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


class ShareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str = Field(min_length=1, max_length=80)
    level: Literal["read", "draft"] = "read"


def _projects_for(user: str) -> list[dict]:
    from hydrahive.projects._config_io import list_for_user
    return [{"id": p["id"], "name": p.get("name", "")} for p in list_for_user(user)]


@router.get("/accounts/{aid}/shares")
def list_shares(aid: str, auth: Auth) -> dict:
    try:
        items = shares.list_for(auth[0], aid)
    except shares.NotFound:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    projects = _projects_for(auth[0])
    names = {f"project:{p['id']}": p["name"] for p in projects}
    return {"shares": [{**s, "name": names.get(s["target"], "")} for s in items], "projects": projects,
            "audit": agent_audit.for_account(aid, 20)}


@router.put("/accounts/{aid}/shares")
def put_share(aid: str, body: ShareIn, auth: Auth) -> dict:
    try:
        return shares.put(auth[0], aid, body.target, body.level)
    except shares.NotFound:
        raise coded(status.HTTP_404_NOT_FOUND, "not_found") from None
    except ValueError as e:
        raise coded(422, "invalid", message=str(e)) from None


@router.delete("/accounts/{aid}/shares/{target}", status_code=status.HTTP_204_NO_CONTENT)
def delete_share(aid: str, target: str, auth: Auth) -> Response:
    if not accounts.get_own(auth[0], aid):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    if not shares.remove(auth[0], aid, target):
        raise coded(status.HTTP_404_NOT_FOUND, "not_found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
