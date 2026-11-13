"""Schnittstellen Zusätze /api/modules/tvwerkstatt/devices/{id}/addons… und Bilder des Katalogs. Nur Admins.

Katalog laden liest nur. Bauen + Installieren und Entfernen nur mit Rückfrage-Kennzeichen.
"""
from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import FileResponse
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import addon_jobs, addons, jobs
from .routes_look import Admin, _guard, _known, _start

router = APIRouter()
_KINDS = ("addon_catalog", "addon_install", "addon_remove")


class Pick(BaseModel):
    model_config = ConfigDict(extra="ignore")
    confirm: bool = False
    addon: str = ""


@router.get("/devices/{device_id}/addons")
def get_addons(device_id: str, p: Admin) -> dict:
    _known(device_id)
    last = [j | {"kind": k} for k in _KINDS if (j := jobs.last_job(k, device_id))]
    return {**addon_jobs.view(device_id), "job": max(last, key=lambda j: j["created_at"]) if last else None}


@router.get("/addons/{addon_id}/image")
def addon_image(addon_id: str, p: Admin) -> FileResponse:
    path = addon_jobs.image(addon_id)
    if path is None:
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_addon_unknown")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.post("/devices/{device_id}/addons/catalog", status_code=status.HTTP_202_ACCEPTED)
async def load_catalog(device_id: str, p: Admin) -> dict:
    _known(device_id)
    await _guard()
    return _start("addon_catalog", device_id, p.username, addon_jobs.run_catalog)


async def _pick(device_id: str, p: Admin, body: Pick, kind: str, make) -> dict:
    _known(device_id)
    if not body.confirm:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_confirm_required")
    try:
        runner = make(device_id, body.addon)
    except addons.TvwAddonError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None
    await _guard()
    return _start(kind, device_id, p.username, runner)


@router.post("/devices/{device_id}/addons/install", status_code=status.HTTP_202_ACCEPTED)
async def install_addon(device_id: str, p: Admin, body: Pick) -> dict:
    """Zusatz bauen und installieren (auch: neu bauen = aktualisieren)."""
    return await _pick(device_id, p, body, "addon_install", addon_jobs.runner_install)


@router.post("/devices/{device_id}/addons/remove", status_code=status.HTTP_202_ACCEPTED)
async def remove_addon(device_id: str, p: Admin, body: Pick) -> dict:
    return await _pick(device_id, p, body, "addon_remove", addon_jobs.runner_remove)
