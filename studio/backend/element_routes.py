"""Studio – REST für Bausteine aus Fotos (Spec „C2 im Detail“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import describe, plan
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}/plan/elements")
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Data = Annotated[dict[str, Any], Body()]


@router.post("/from-image")
def from_image(project_id: str, data: Data, auth: Auth) -> dict:
    """Neuer Baustein mit einem Bild des Projekts als Vorlage-Foto (Bibliothek → „Als Figur anlegen …“)."""
    guard(auth[0], project_id)
    try:
        return describe.from_image(project_id, data)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.post("/{element_id}/describe")
async def describe_element(project_id: str, element_id: str, auth: Auth) -> dict:
    """Beschreibung + Aussehen aus dem ersten Vorlage-Foto (Bild-KI, ≈ 0,1 ct)."""
    guard(auth[0], project_id)
    try:
        return await describe.describe(project_id, element_id)
    except plan.PlanError as e:
        raise coded(e.status, e.code)
