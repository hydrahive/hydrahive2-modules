"""Studio – REST für die Schnittfassung (Spec „Bauplan Etappe 4“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import plan, timeline
from ._guard import guard
from ._store import project_root

router = APIRouter(prefix="/projects/{project_id}/timeline")
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Data = Annotated[Any, Body()]


def _run(project_id: str, fn, *args, **kw) -> dict:
    """Ausführen, Fehlercodes übersetzen; `base` (Projektordner) für /api/files mitgeben – steht nicht in der Datei."""
    try:
        tl = fn(project_id, *args, **kw)
    except plan.PlanError as e:
        raise coded(e.status, e.code)
    return {**tl, "base": str(project_root(project_id))}


@router.get("")
def get_timeline(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(project_id, timeline.load)


@router.put("")
def put_timeline(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(project_id, timeline.save, data)


@router.post("/from-plan")
def from_plan(project_id: str, auth: Auth, data: Data = None) -> dict:
    guard(auth[0], project_id)
    replace = isinstance(data, dict) and data.get("replace") is True
    return _run(project_id, timeline.from_plan, replace=replace)
