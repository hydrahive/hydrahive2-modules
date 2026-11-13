"""Schnittstellen App-Verwaltung /api/modules/tvwerkstatt/devices/{id}/store… Nur Admins.

Lesen ändert nichts. Store öffnen/suchen zeigt am Fernseher den Play Store (Installieren bestätigt man dort).
Deinstallieren nur mit Rückfrage-Kennzeichen und nur nachinstallierte Apps.
"""
from __future__ import annotations

from fastapi import APIRouter, status
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import jobs, store, store_jobs
from .routes_look import Admin, _guard, _known, _start

router = APIRouter()
_KINDS = ("store_read", "store_open", "store_uninstall")


class Open(BaseModel):
    model_config = ConfigDict(extra="ignore")
    package: str | None = None
    query: str | None = None


class Remove(BaseModel):
    model_config = ConfigDict(extra="ignore")
    confirm: bool = False
    package: str = ""


@router.get("/devices/{device_id}/store")
def get_store(device_id: str, p: Admin) -> dict:
    _known(device_id)
    last = [j | {"kind": k} for k in _KINDS if (j := jobs.last_job(k, device_id))]
    return {"view": store_jobs.view(device_id), "job": max(last, key=lambda j: j["created_at"]) if last else None}


@router.post("/devices/{device_id}/store/read", status_code=status.HTTP_202_ACCEPTED)
async def read_store(device_id: str, p: Admin) -> dict:
    _known(device_id)
    await _guard()
    return _start("store_read", device_id, p.username, store_jobs.run_read)


@router.post("/devices/{device_id}/store/open", status_code=status.HTTP_202_ACCEPTED)
async def open_store(device_id: str, p: Admin, body: Open) -> dict:
    """Play Store am Fernseher öffnen: bei einer App oder mit Suche."""
    _known(device_id)
    if bool(body.package) == bool(body.query):
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_store_bad_query")
    try:
        runner = store_jobs.runner_open(body.package, body.query)
    except store.TvwStoreError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None
    await _guard()
    return _start("store_open", device_id, p.username, runner)


@router.post("/devices/{device_id}/store/uninstall", status_code=status.HTTP_202_ACCEPTED)
async def uninstall(device_id: str, p: Admin, body: Remove) -> dict:
    _known(device_id)
    if not body.confirm:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_confirm_required")
    try:
        runner = store_jobs.runner_uninstall(device_id, body.package)
    except store.TvwStoreError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None
    await _guard()
    return _start("store_uninstall", device_id, p.username, runner)
