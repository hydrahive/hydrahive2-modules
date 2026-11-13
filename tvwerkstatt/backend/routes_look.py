"""Schnittstellen Desktop/Aussehen /api/modules/tvwerkstatt/devices/{id}/… (PLAN-E2.md). Nur Admins.

Aussehen lesen/speichern, Apps lesen (Auftrag), Bilder der Apps, Hintergründe hochladen/löschen/ansehen,
Aussehen auf den Fernseher schieben (Auftrag, nur mit Rückfrage).
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict

from . import apps, container, incus, jobs, look, look_jobs, state, wallpapers

router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]
_tasks: set[asyncio.Task] = set()


class Confirm(BaseModel):
    model_config = ConfigDict(extra="ignore")
    confirm: bool = False


def _known(device_id: str) -> None:
    if not any(d["device_id"] == device_id for d in state.devices()):
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_device_not_found")


def _start(kind: str, device_id: str, admin: str, runner) -> dict:
    try:
        job_id = jobs.begin(kind, device_id, admin, "container")
    except jobs.JobError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code) from None
    task = asyncio.create_task(runner(job_id, device_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"job_id": job_id}


@router.get("/devices/{device_id}/desktop")
def get_desktop(device_id: str, p: Admin) -> dict:
    """Alles für den Reiter Desktop: Aussehen, Apps des Fernsehers, Hintergründe, letzte Aufträge, Stand des Schiebens."""
    _known(device_id)
    with look_jobs.db() as conn:
        r = conn.execute("SELECT pushed_at, pushed_hash FROM module_tvwerkstatt_looks WHERE device_id = ?",
                         (device_id,)).fetchone()
    pushed_at, pushed_hash = (r[0], r[1]) if r else ("", "")
    _, _, digest = look_jobs.bundle(device_id)
    return {"look": look.load(device_id), "apps": look_jobs.known_apps(device_id),
            "wallpapers": wallpapers.list_for(device_id), "pushed_at": pushed_at,
            "pushed_current": bool(pushed_hash) and pushed_hash == digest,
            "read_job": jobs.last_job("apps", device_id), "push_job": jobs.last_job("look", device_id)}


@router.put("/devices/{device_id}/look")
def put_look(device_id: str, p: Admin, body: dict) -> dict:
    _known(device_id)
    try:
        return {"look": look.save(device_id, body)}
    except look.TvwLookError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code, field=exc.field) from None


async def _guard() -> None:
    if not incus.available():
        raise coded(status.HTTP_409_CONFLICT, "tvw_no_incus")
    if await container.status() == "missing":
        raise coded(status.HTTP_409_CONFLICT, "tvw_not_set_up")


@router.post("/devices/{device_id}/apps/read", status_code=status.HTTP_202_ACCEPTED)
async def read_apps(device_id: str, p: Admin) -> dict:
    """Apps vom Fernseher lesen – nur lesend."""
    _known(device_id)
    await _guard()
    return _start("apps", device_id, p.username, look_jobs.run_read_apps)


@router.post("/devices/{device_id}/look/push", status_code=status.HTTP_202_ACCEPTED)
async def push_look(device_id: str, p: Admin, body: Confirm) -> dict:
    """Nur das Aussehen auf den Fernseher schieben (kein Neubau). Schaltet am Fernseher → Rückfrage."""
    if not body.confirm:
        raise coded(status.HTTP_400_BAD_REQUEST, "tvw_confirm_required")
    _known(device_id)
    await _guard()
    return _start("look", device_id, p.username, look_jobs.run_push_look)


@router.get("/devices/{device_id}/apps/{package}/image")
def app_image(device_id: str, package: str, p: Admin) -> Response:
    _known(device_id)
    if not apps._PKG.match(package):
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_image_not_found")
    f = apps.image_dir(device_id) / f"{package}.png"
    if not f.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_image_not_found")
    return Response(f.read_bytes(), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@router.post("/devices/{device_id}/wallpapers")
async def upload_wallpaper(device_id: str, p: Admin, mood: Annotated[str, Form()],
                           file: Annotated[UploadFile, File()], title: Annotated[str, Form()] = "") -> dict:
    _known(device_id)
    data = await file.read(wallpapers.MAX_UPLOAD + 1)
    try:
        return {"wallpaper": await asyncio.to_thread(wallpapers.add, device_id, mood, data, title or file.filename or "")}
    except wallpapers.TvwWallpaperError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None


@router.delete("/devices/{device_id}/wallpapers/{wallpaper_id}")
def delete_wallpaper(device_id: str, wallpaper_id: str, p: Admin) -> dict:
    _known(device_id)
    try:
        wallpapers.remove(device_id, wallpaper_id)
    except wallpapers.TvwWallpaperError as exc:
        raise coded(status.HTTP_404_NOT_FOUND, exc.code) from None
    return {"ok": True}


@router.get("/devices/{device_id}/wallpapers/{wallpaper_id}/image")
def wallpaper_image(device_id: str, wallpaper_id: str, p: Admin) -> Response:
    _known(device_id)
    w = next((x for x in wallpapers.list_for(device_id) if x["wallpaper_id"] == wallpaper_id), None)
    f = wallpapers.folder(device_id) / w["file_name"] if w else None
    if f is None or not f.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_image_not_found")
    return Response(f.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})
