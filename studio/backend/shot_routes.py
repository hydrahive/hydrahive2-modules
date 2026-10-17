"""Studio – REST für Shots und Regie-Agent (Spec „Bauplan 2b“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import director, plan, shots
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}/plan/scenes/{scene_id}")
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Data = Annotated[dict[str, Any], Body()]


def _run(fn, *args):
    try:
        return fn(*args)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.post("/shots")
def add_shot(project_id: str, scene_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(shots.add, project_id, scene_id, data)


@router.put("/shots/order")
def order_shots(project_id: str, scene_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    ids = data.get("shot_ids")
    return {"shots": _run(shots.reorder, project_id, scene_id, ids if isinstance(ids, list) else [])}


@router.put("/shots/{shot_id}")
def update_shot(project_id: str, scene_id: str, shot_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(shots.update, project_id, scene_id, shot_id, data)


@router.delete("/shots/{shot_id}")
def delete_shot(project_id: str, scene_id: str, shot_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    _run(shots.delete, project_id, scene_id, shot_id)
    return {"deleted": shot_id}


@router.post("/decompose")
async def decompose(project_id: str, scene_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    try:
        result = await director.decompose(project_id, scene_id, replace=data.get("replace") is True)
    except plan.PlanError as e:
        raise coded(e.status, e.code)
    return {"shots": result, "count": len(result)}
