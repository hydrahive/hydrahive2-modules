"""Schnittstellen /api/modules/tvwerkstatt (PLAN-E1.md). Nur Admins.

Fehler kommen als Code (`tvw_…`), nie als Text mit Pfaden oder Ausgaben vom Server. Die Ausgabe eines gescheiterten
Einrichtungsschritts (bereinigt, gekürzt) steht im Auftrag – der Admin soll sehen können, wo es hing.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import container, incus, jobs, state

logger = logging.getLogger(__name__)
router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]
_tasks: set[asyncio.Task] = set()                    # starke Verweise, sonst räumt Python laufende Aufträge weg


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SetupBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    accept_license: bool = False


async def _background(coro) -> None:
    try:
        await coro
    except jobs.JobError as exc:
        logger.warning("TV-Werkstatt: Auftrag endete mit %s", exc.code)
    except Exception:
        logger.exception("TV-Werkstatt: Auftrag fehlgeschlagen")


@router.get("/state")
async def get_state(p: Admin) -> dict:
    """Ohne incus kein Fehler, sondern ein Zustand, den die Seite erklären kann."""
    if not incus.available():
        return {"incus": False, "error_code": "tvw_no_incus", "devices": [], "builds": [],
                "container": "missing", "setup": None}
    devices = [{**d, "check": jobs.last_job("probe", d["device_id"])} for d in state.devices()]
    return {"incus": True, "error_code": "", "devices": devices, "builds": state.builds(),
            "container": await container.status(), "setup": jobs.last_setup()}


@router.post("/setup", status_code=status.HTTP_202_ACCEPTED)
async def start_setup(p: Admin, body: SetupBody) -> dict:
    """Werkstatt einrichten oder nach einem Fehler ab dem gescheiterten Schritt weitermachen."""
    if not incus.available():
        raise coded(status.HTTP_409_CONFLICT, "tvw_no_incus")
    start_at = jobs.retry_step()
    try:
        job_id = jobs.begin_setup(p.username, license_accepted=body.accept_license)
    except jobs.JobError as exc:
        code = status.HTTP_400_BAD_REQUEST if exc.code == "tvw_license_required" else status.HTTP_409_CONFLICT
        raise coded(code, exc.code) from None
    task = asyncio.create_task(_background(jobs.run_setup(job_id, start_at=start_at)))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"job_id": job_id}


async def _container_action(action) -> dict:
    if jobs.busy():
        raise coded(status.HTTP_409_CONFLICT, "tvw_busy")
    try:
        await action()
    except container.TvwContainerError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code) from None
    return {"container": await container.status()}


@router.post("/container/stop")
async def stop_container(p: Admin, body: Empty) -> dict:
    return await _container_action(container.stop)


@router.delete("/container")
async def delete_container(p: Admin) -> dict:
    """Werkstatt abbauen. Der gesicherte Signierschlüssel bleibt im Datenordner."""
    return await _container_action(container.remove)
