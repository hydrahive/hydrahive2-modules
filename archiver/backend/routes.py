"""Archiver API: Drives, Jobs, SSE-Stream, Wallet-Scan."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Annotated

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db
from hydrahive.projects._paths import workspace_path, ensure_workspace

from .drives import list_drives, mount_drive, unmount_drive
from . import jobs as job_mgr

router = APIRouter()

_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


class MountBody(BaseModel):
    device: str = Field(min_length=5, max_length=64)


class UnmountBody(BaseModel):
    mountpoint: str = Field(min_length=10, max_length=256)


class RemountBody(BaseModel):
    device: str = Field(min_length=5, max_length=64)
    mountpoint: str = Field(min_length=10, max_length=256)


class StartJobBody(BaseModel):
    drive_path: str = Field(min_length=1, max_length=512)
    drive_label: str = Field(default="", max_length=256)
    project_id: str = Field(min_length=1, max_length=128)
    folder_name: str = Field(min_length=1, max_length=256)


# ── Drives ────────────────────────────────────────────────────────

@router.get("/drives")
def get_drives(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    return [
        {"name": d.name, "label": d.label, "size": d.size,
         "mountpoint": d.mountpoint, "transport": d.transport, "device": d.device}
        for d in list_drives()
    ]


@router.post("/drives/mount")
def mount_device(body: MountBody, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    try:
        mountpoint = mount_drive(body.device)
    except (ValueError, RuntimeError) as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"mountpoint": mountpoint}


@router.post("/drives/unmount")
def unmount_device(body: UnmountBody, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    try:
        unmount_drive(body.mountpoint)
    except (ValueError, RuntimeError) as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True}


@router.post("/drives/remount")
def remount_device(body: RemountBody, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    try:
        unmount_drive(body.mountpoint)
    except (ValueError, RuntimeError):
        pass  # war vielleicht schon weg — trotzdem neu mounten
    try:
        mountpoint = mount_drive(body.device)
    except (ValueError, RuntimeError) as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"mountpoint": mountpoint}


# ── Jobs ──────────────────────────────────────────────────────────

@router.get("/jobs")
def list_jobs(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, _ = auth
    # In-memory running jobs for this user + DB history
    running = [j.to_dict() | {"started_at": None, "finished_at": None}
               for j in job_mgr.get_all_jobs() if j.user == user]
    running_ids = {j["id"] for j in running}

    with db() as c:
        rows = c.execute(
            "SELECT id, drive_label, project_id, folder_name, target_path, "
            "status, pct, files_done, files_total, error_count, started_at, finished_at "
            "FROM module_archiver_jobs WHERE \"user\" = ? ORDER BY started_at DESC LIMIT 50",
            (user,),
        ).fetchall()

    history = [dict(r) for r in rows if r["id"] not in running_ids]
    return running + history


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def start_job(body: StartJobBody, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth

    ws = ensure_workspace(body.project_id)
    target = str(ws / body.folder_name)

    with db() as c:
        cur = c.execute(
            "INSERT INTO module_archiver_jobs "
            "(\"user\", drive_path, drive_label, project_id, folder_name, target_path) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user, body.drive_path, body.drive_label, body.project_id, body.folder_name, target),
        )
        job_id = cur.lastrowid

    job = job_mgr.Job(
        id=job_id, user=user,
        drive_path=body.drive_path, drive_label=body.drive_label,
        project_id=body.project_id, folder_name=body.folder_name,
        target_path=target,
    )
    job_mgr.start_job(job)
    return {"id": job_id, "target_path": target}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    if not job_mgr.cancel_job(job_id):
        raise coded(status.HTTP_404_NOT_FOUND, "job_not_found_or_not_running")
    return {"ok": True}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> StreamingResponse:
    user, _ = auth

    async def _events():
        yield ": connected\n\n"
        while True:
            job = job_mgr.get_job(job_id)
            if job is None or job.user != user:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                break
            yield f"data: {json.dumps(job.to_dict())}\n\n"
            if job.status in ("done", "failed", "cancelled"):
                _persist_finished(job)
                break
            await asyncio.sleep(0.8)

    return StreamingResponse(
        _events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/wallets")
def scan_wallets(job_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        row = c.execute(
            "SELECT target_path, status FROM module_archiver_jobs WHERE id = ? AND \"user\" = ?",
            (job_id, user),
        ).fetchone()
    if not row:
        raise coded(status.HTTP_404_NOT_FOUND, "job_not_found")
    return {"wallets": job_mgr.scan_wallets(row["target_path"])}


# ── Log ───────────────────────────────────────────────────────────

@router.get("/log")
def get_log(
    auth: Annotated[tuple[str, str], Depends(require_auth)],
    n: int = 100,
) -> dict:
    """Letzten N relevanten Log-Zeilen aus journald (nur archiver-Meldungen)."""
    n = min(max(n, 10), 500)
    try:
        out = subprocess.run(
            ["sudo", "/bin/bash", "-c",
             f"journalctl -u hydrahive2 -n {n * 5} --no-pager -o short 2>&1"],
            capture_output=True, text=True, timeout=10,
        )
        all_lines = out.stdout.splitlines()
        lines = [l for l in all_lines if "archiver" in l.lower()][-n:]
        if not lines and all_lines:
            # Fallback: letzte n Zeilen ohne Filter zeigen
            lines = all_lines[-n:]
    except Exception as exc:
        logger.warning("archiver log: journalctl fehlgeschlagen: %s", exc)
        lines = [f"[Kein journald-Zugriff: {exc}]"]
    return {"lines": lines}


# ── Intern ────────────────────────────────────────────────────────

def _persist_finished(job: job_mgr.Job) -> None:
    with db() as c:
        c.execute(
            f"UPDATE module_archiver_jobs SET status=?, pct=?, files_done=?, files_total=?, "
            f"error_count=?, finished_at={_NOW} WHERE id=?",
            (job.status, job.pct, job.files_done, job.files_total, job.error_count, job.id),
        )
