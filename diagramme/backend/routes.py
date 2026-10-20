"""Routen mit Login (/api/modules/diagramme/…): signierte Ansichts-Adresse. Sammlung folgt in S2."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import links, store

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


@router.get("/view-link/{view_id}")
def view_link(view_id: str, auth: Auth) -> dict:
    """Für den Chat-Rahmen (Kern: module_view). Fremde oder unbekannte Diagramme → 404."""
    if not store.can_view(store.get(view_id), auth[0], auth[1]):
        raise coded(404, "diagram_not_found")
    return {"url": links.view_url(view_id)}
