"""Schnittstellen /api/modules/tvwerkstatt/devices (PLAN-E1.md Baustein 5). Nur Admins.

Eintragen startet sofort das Prüfen (nur lesend). Fehler kommen als Code (`tvw_…`).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import container, device, device_jobs, incus, install_jobs, jobs, state

logger = logging.getLogger(__name__)
router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]
_tasks: set[asyncio.Task] = set()


class NewDevice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=device.MAX_NAME)
    address: str = Field(min_length=7, max_length=15)
    port: int = Field(default=5555, ge=1, le=65535)


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Confirm(BaseModel):
    model_config = ConfigDict(extra="ignore")
    confirm: bool = False                       # Rückfrage auf der Seite bestätigt


async def _guard() -> None:
    if not incus.available():
        raise coded(status.HTTP_409_CONFLICT, "tvw_no_incus")
    if await container.status() == "missing":
        raise coded(status.HTTP_409_CONFLICT, "tvw_not_set_up")


def _start(kind: str, device_id: str, admin: str, runner) -> str:
    try:
        job_id = jobs.begin(kind, device_id, admin, "container" if kind != "probe" else "network")
    except jobs.JobError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code) from None
    task = asyncio.create_task(runner(job_id, device_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job_id


@router.post("/devices", status_code=status.HTTP_202_ACCEPTED)
async def add_device(p: Admin, body: NewDevice) -> dict:
    await _guard()
    if jobs.busy():
        raise coded(status.HTTP_409_CONFLICT, "tvw_busy")
    try:
        device_id = device_jobs.add(body.name, body.address.strip(), body.port, p.username)
    except device.TvwDeviceError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST if exc.code != "tvw_device_exists" else status.HTTP_409_CONFLICT,
                    exc.code) from None
    return {"device_id": device_id, "job_id": _start("probe", device_id, p.username, device_jobs.run_check)}


@router.post("/devices/{device_id}/check", status_code=status.HTTP_202_ACCEPTED)
async def check_device(device_id: str, p: Admin, body: Empty) -> dict:
    await _guard()
    _known(device_id)
    return {"job_id": _start("probe", device_id, p.username, device_jobs.run_check)}


def _known(device_id: str) -> None:
    if not any(d["device_id"] == device_id for d in state.devices()):
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_device_not_found")


@router.post("/devices/{device_id}/install", status_code=status.HTTP_202_ACCEPTED)
async def install_home(device_id: str, p: Admin, body: Confirm) -> dict:
    """Startbildschirm aufspielen und zu Home machen – schaltet am Fernseher, darum nur mit Rückfrage."""
    if not body.confirm:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_confirm_required")
    await _guard()
    _known(device_id)
    if install_jobs.good_build() is None:
        raise coded(status.HTTP_409_CONFLICT, "tvw_no_build")
    return {"job_id": _start("install", device_id, p.username, install_jobs.run_install)}


@router.post("/devices/{device_id}/restore", status_code=status.HTTP_202_ACCEPTED)
async def restore_home(device_id: str, p: Admin, body: Confirm) -> dict:
    """Zurück zum Original-Startbildschirm. Unser Startbildschirm bleibt installiert, ist nur nicht mehr Home."""
    if not body.confirm:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_confirm_required")
    await _guard()
    _known(device_id)
    return {"job_id": _start("restore", device_id, p.username, install_jobs.run_restore)}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, p: Admin) -> dict:
    if jobs.busy():
        raise coded(status.HTTP_409_CONFLICT, "tvw_busy")
    try:
        await device_jobs.remove(device_id)
    except device.TvwDeviceError as exc:
        raise coded(status.HTTP_404_NOT_FOUND, exc.code) from None
    return {"ok": True}
