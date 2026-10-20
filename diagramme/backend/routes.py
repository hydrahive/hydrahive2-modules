"""Routen mit Login (/api/modules/diagramme/…): signierte Ansichts-Adresse, Sammlung (S2), Freischalten (S2)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import require_admin, require_auth
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, StrictBool

from . import agents_access, links, store
from .collection import router as collection_router

router = APIRouter()
router.include_router(collection_router)
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Admin = Annotated[tuple[str, str], Depends(require_admin)]


class AccessIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    on: StrictBool


@router.get("/view-link/{view_id}")
def view_link(view_id: str, auth: Auth) -> dict:
    """Für den Chat-Rahmen (Kern: module_view). Fremde oder unbekannte Diagramme → 404."""
    if not store.can_view(store.get(view_id), auth[0], auth[1]):
        raise coded(404, "diagram_not_found")
    return {"url": links.view_url(view_id)}


@router.get("/agents-access")
def agents_access_status(_: Admin) -> dict:
    return agents_access.status()


@router.post("/agents-access")
def agents_access_set(body: AccessIn, _: Admin) -> dict:
    """Für alle Agenten freischalten (on=true) oder genau die dadurch ergänzten wieder zurücknehmen (on=false)."""
    res = agents_access.unlock() if body.on else agents_access.relock()
    return dict(res, **agents_access.status())
