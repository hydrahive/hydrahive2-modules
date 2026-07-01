"""Video-Editor — dateibasierter Job-Store für Proxy-/Export-Jobs.

Analog zum atelier/backend/_jobstore.py-Muster: Jobs liegen als
``<dir>/<job_id>.json`` im Projekt-Workspace, Status wird gepollt.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_job(job_dir: Path, job_id: str, *, kind: str, file_id: str) -> dict:
    job = {
        "job_id": job_id,
        "kind": kind,          # "proxy" | "export"
        "file_id": file_id,
        "status": "running",   # running | done | failed
        "error": None,
        "created_at": now(),
        "finished_at": None,
    }
    write_job(job_dir, job)
    return job


def write_job(job_dir: Path, job: dict) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / f"{job['job_id']}.json").write_text(
        json.dumps(job, ensure_ascii=False, indent=2), "utf-8"
    )


def read_job(job_dir: Path, job_id: str) -> dict | None:
    p = job_dir / f"{job_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def finish_job(job_dir: Path, job_id: str, *, ok: bool, error: str | None = None) -> None:
    job = read_job(job_dir, job_id)
    if not job:
        return
    job["status"] = "done" if ok else "failed"
    job["error"] = error
    job["finished_at"] = now()
    write_job(job_dir, job)
