"""App bauen und herunterladen: /api/modules/tvwerkstatt/app/build, /app/apk (Login + Admin; PLAN-APP.md G2)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, status
from fastapi.responses import FileResponse
from hydrahive.api.middleware.errors import coded

from . import app_build, container, incus, jobs
from .routes import Empty, _background, _tasks
from .routes_look import Admin

router = APIRouter()


@router.post("/app/build", status_code=status.HTTP_202_ACCEPTED)
async def start_app_build(p: Admin, body: Empty) -> dict:
    """HydraHive-App im Container bauen. Am Fernseher passiert dabei nichts."""
    if not incus.available():
        raise coded(status.HTTP_409_CONFLICT, "tvw_no_incus")
    if await container.status() == "missing":
        raise coded(status.HTTP_409_CONFLICT, "tvw_not_set_up")
    try:
        job_id = jobs.begin("app_build", app_build.PART, p.username, "container")
    except jobs.JobError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code) from None
    task = asyncio.create_task(_background(app_build.run(job_id)))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"job_id": job_id}


@router.get("/app/apk")
def download_apk(p: Admin) -> FileResponse:
    path, good = app_build.apk_path(), app_build.last_good()
    if path is None or good is None:
        raise coded(status.HTTP_404_NOT_FOUND, "tvw_app_no_build")
    version = good["version"].split(" ")[0] or "app"
    return FileResponse(path, media_type="application/vnd.android.package-archive",
                        filename=f"hydrahive-{version}.apk", headers={"Cache-Control": "no-store"})


def build_view() -> dict:
    """Für /app/devices: letzter Auftrag „App bauen“ und die zuletzt gebaute App (falls herunterladbar)."""
    good = app_build.last_good() if app_build.apk_path() else None
    apk = {k: good[k] for k in ("version", "size", "sha256", "created_at")} if good else None
    return {"build": jobs.last_job("app_build"), "apk": apk}
