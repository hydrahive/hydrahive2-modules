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

from . import container, device, device_jobs, incus, jobs, state

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


async def _guard() -> None:
    if not incus.available():
        raise coded(status.HTTP_409_CONFLICT, "tvw_no_incus")
    if await container.status() == "missing":
        raise coded(status.HTTP_409_CONFLICT, "tvw_not_set_up")


def _start_check(device_id: str, admin: str) -> str:
    try:
        job_id = jobs.begin("probe", device_id, admin, "network")
    except jobs.JobError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code) from None
    task = asyncio.create_task(device_jobs.run_check(job_id, device_id))
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
    return {"device_id": device_id, "job_id": _start_check(device_id, p.username)}


@router.post("/devices/{device_id}/check", status_code=status.HTTP_202_ACCEPTED)
async def check_device(device_id: str, p: Admin, body: Empty) -> dict:
    await _guard()
    if not any(d["device_id"] == device_id for d in state.devices()):
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_device_not_found")
    return {"job_id": _start_check(device_id, p.username)}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, p: Admin) -> dict:
    if jobs.busy():
        raise coded(status.HTTP_409_CONFLICT, "tvw_busy")
    try:
        await device_jobs.remove(device_id)
    except device.TvwDeviceError as exc:
        raise coded(status.HTTP_404_NOT_FOUND, exc.code) from None
    return {"ok": True}
