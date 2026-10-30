"""Schnittstellen /api/modules/hydralabor (PLAN-L1.md „Assistent“, „Labor-Seite“). Nur Admins.

Lange Aufträge (anlegen, zurücksetzen, Netz prüfen, Testlauf, entfernen) laufen im Hintergrund (202); die Seite fragt
`GET /state` ab. Der Zustand nennt keine Netz-Interna, nur was die Oberfläche braucht.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import checks, container, jobs, lab_project, state
from .container import LaborError, Limits

router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]
_PUBLIC = ("step", "running", "progress", "error_code", "error_step", "model", "cpu", "ram_mb", "disk_gb",
           "last_net_ok", "last_test")


class LimitsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpu: int = 2
    ram_mb: int = 4096
    disk_gb: int = 20


class CreateIn(LimitsIn):
    model: str = Field(min_length=1, max_length=200)


class RemoveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: str = Field(max_length=20)


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


def _limits(body: LimitsIn) -> Limits:
    try:
        return Limits(cpu=body.cpu, ram_mb=body.ram_mb, disk_gb=body.disk_gb)
    except LaborError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code) from None


def _start(job: str) -> dict:
    if not jobs.start(job):
        raise coded(status.HTTP_409_CONFLICT, "labor_busy")
    return {"started": job}


def _ready() -> None:
    if state.get()["step"] != "ready":
        raise coded(status.HTTP_409_CONFLICT, "labor_not_ready")


@router.get("/state")
async def get_state(p: Admin) -> dict:
    s = state.get()
    out = {k: s[k] for k in _PUBLIC}
    out["project_id"] = s["made"].get("project_id", "")
    out["agent_id"] = s["made"].get("agent_id", "")
    out["container_running"] = await container.running() if s["step"] == "ready" else False
    return out


@router.get("/models")
async def models(p: Admin) -> dict:
    from hydrahive.llm import registry
    items = await registry.list_models("chat")
    return {"items": [{"id": m.id, "label": m.label, "provider": m.provider} for m in items]}


@router.post("/checks")
async def run_checks(p: Admin, body: LimitsIn) -> dict:
    lim = _limits(body)
    return await checks.run(disk_gb=lim.disk_gb, ram_mb=lim.ram_mb)


@router.post("/create", status_code=status.HTTP_202_ACCEPTED)
def create(p: Admin, body: CreateIn) -> dict:
    lim = _limits(body)
    if state.get()["step"] == "ready":
        raise coded(status.HTTP_409_CONFLICT, "labor_already_ready")
    try:
        lab_project._check_model(body.model)
    except LaborError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, e.code) from None
    if state.get()["running"]:
        raise coded(status.HTTP_409_CONFLICT, "labor_busy")
    state.save_choice(model=body.model, cpu=lim.cpu, ram_mb=lim.ram_mb, disk_gb=lim.disk_gb, admin=p.username)
    return _start("create")


@router.post("/reset", status_code=status.HTTP_202_ACCEPTED)
def reset(p: Admin, body: Empty) -> dict:
    _ready()
    return _start("reset")


@router.post("/probe", status_code=status.HTTP_202_ACCEPTED)
def probe(p: Admin, body: Empty) -> dict:
    _ready()
    return _start("probe")


@router.post("/test", status_code=status.HTTP_202_ACCEPTED)
def test(p: Admin, body: Empty) -> dict:
    _ready()
    return _start("test")


@router.post("/remove", status_code=status.HTTP_202_ACCEPTED)
def remove(p: Admin, body: RemoveIn) -> dict:
    if body.confirm != "LABOR":
        raise coded(status.HTTP_400_BAD_REQUEST, "labor_confirm_missing")
    return _start("remove")


@router.post("/{action}")
async def power(p: Admin, action: Literal["start", "stop"], body: Empty) -> dict:
    _ready()
    if state.get()["running"]:
        raise coded(status.HTTP_409_CONFLICT, "labor_busy")
    await (container.start() if action == "start" else container.stop())
    return {"running": await container.running()}
