"""Studio – REST für „Planen“ (Spec „Bauplan Etappe 2“). Alle Routen prüfen Mitgliedschaft."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import batch, free_images, import_atelier, jobs, plan
from ._guard import guard

router = APIRouter(prefix="/projects/{project_id}/plan")
Auth = Annotated[tuple[str, str], Depends(require_auth)]
Data = Annotated[dict[str, Any], Body()]


def _run(fn, *args):
    try:
        return fn(*args)
    except plan.PlanError as e:
        raise coded(e.status, e.code)


@router.get("")
def get_plan(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    jobs.recover(project_id)                      # liegengebliebene Aufträge (Neustart) zuerst bereinigen
    return plan.get_plan(project_id)


@router.put("/screenplay")
def put_head(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return plan.save_head(project_id, {k: v for k, v in data.items() if k != "scene_order"})


@router.put("/order")
def put_order(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    order = data.get("scene_order")
    return plan.reorder(project_id, order if isinstance(order, list) else [])


@router.post("/scenes")
def post_scene(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(plan.save_scene, project_id, data)


@router.put("/scenes/{scene_id}")
def put_scene(project_id: str, scene_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(plan.save_scene, project_id, data, scene_id)


@router.delete("/scenes/{scene_id}")
def del_scene(project_id: str, scene_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    _run(plan.delete_scene, project_id, scene_id)
    return {"deleted": scene_id}


@router.post("/elements")
def post_element(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(plan.save_element, project_id, data)


@router.put("/elements/{element_id}")
def put_element(project_id: str, element_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(plan.save_element, project_id, data, element_id)


@router.delete("/elements/{element_id}")
def del_element(project_id: str, element_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    _run(plan.delete_element, project_id, element_id)
    return {"deleted": element_id}


@router.get("/import/atelier")
def import_preview(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return import_atelier.preview(project_id)


@router.post("/import/atelier")
def import_run(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(import_atelier.run, project_id)


@router.get("/jobs")
def list_jobs(project_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    jobs.recover(project_id)
    return {"jobs": jobs.list_jobs(project_id)}


@router.get("/batch/{kind}")
def batch_preview(project_id: str, kind: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(batch.preview, project_id, kind)


@router.post("/batch/{kind}", status_code=202)
def batch_start(project_id: str, kind: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(batch.start, project_id, kind)


@router.post("/free-images", status_code=202)
def free_start(project_id: str, data: Data, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(free_images.start, project_id, data)


@router.post("/jobs/{job_id}/cancel")
def job_cancel(project_id: str, job_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    return _run(jobs.cancel, project_id, job_id)
