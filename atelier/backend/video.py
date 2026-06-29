"""Atelier — Video-Jobs (Image-to-Video, asynchron).

Video dauert 30-90s → wird NICHT im Request erzeugt. Muster wie deepresearch:
``start_video_job`` legt einen Job an und startet einen Hintergrund-Task
(submit → poll-Schleife → download), der den Status in eine Job-Datei schreibt.
Das Frontend pollt die Job-Liste bis ``completed``/``failed``.

Wiederverwendet die Core-Bausteine aus ``hydrahive.tools._openrouter_video``
(submit_video_job, poll_video_job, download_video) — kein eigener HTTP-Code.

Job-Store dateibasiert: ``atelier/videos/<job_id>.json``. Fertige Videos liegen
als ``atelier/videos/<uuid>.mp4`` daneben.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from hydrahive.llm._config import openrouter_key
from hydrahive.tools._openrouter_video import (
    download_video,
    poll_video_job,
    submit_video_job,
)

from . import storage

logger = logging.getLogger("hhmod_atelier.video")

_DEFAULT_MODEL = "minimax/hailuo-2.3"
_POLL_INTERVAL = 5.0
_MAX_POLLS = 90  # ~7,5 min Obergrenze
_SEM = asyncio.Semaphore(2)  # max 2 parallele Video-Jobs


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _job_path(project_id: str, job_id: str):
    return storage.videos_dir(project_id) / f"{job_id}.json"


def _write_job(project_id: str, job: dict) -> None:
    path = _job_path(project_id, job["job_id"])
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), "utf-8")


def list_video_jobs(project_id: str) -> list[dict]:
    """Alle Video-Jobs des Projekts (neueste zuerst)."""
    vdir = storage.videos_dir(project_id)
    jobs: list[dict] = []
    for p in vdir.glob("*.json"):
        try:
            jobs.append(json.loads(p.read_text("utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    jobs.sort(key=lambda j: j.get("created_at") or "", reverse=True)
    return jobs


def start_video_job(project_id: str, req: dict) -> dict:
    """Legt einen Video-Job an und startet den Hintergrund-Task. Gibt den Job zurück."""
    job_id = storage.new_id()
    source_rel = str(req.get("source_rel") or "")
    job = {
        "job_id": job_id,
        "status": "pending",
        "source_rel": source_rel,
        "prompt": str(req.get("prompt") or "")[:2000],
        "model": str(req.get("model") or "").strip() or _DEFAULT_MODEL,
        "duration": int(req.get("duration") or 5),
        "aspect_ratio": str(req.get("aspect_ratio") or "16:9")[:16],
        "video_rel": None,
        "error": None,
        "created_at": _now(),
    }
    _write_job(project_id, job)
    asyncio.create_task(_run_job(project_id, job))
    return job


async def _run_job(project_id: str, job: dict) -> None:
    """Hintergrund-Task: submit → poll bis fertig → download. Schreibt Status."""
    async with _SEM:
        try:
            key = openrouter_key()
            if not key:
                raise RuntimeError("Kein OpenRouter-API-Key konfiguriert.")
            image_url = _source_to_data_url(project_id, job["source_rel"])
            job["status"] = "processing"
            _write_job(project_id, job)

            remote_id = await submit_video_job(
                job["prompt"], job["model"], key=key,
                duration=job["duration"], aspect_ratio=job["aspect_ratio"],
                image_url=image_url,
            )
            url = await _poll_until_done(remote_id, key=key)
            path = await download_video(url, storage.videos_dir(project_id), key=key)

            job["status"] = "completed"
            job["video_rel"] = f"videos/{path.name}"
            _write_job(project_id, job)
            logger.info("atelier video done: job=%s file=%s", job["job_id"], path.name)
        except Exception as e:  # noqa: BLE001 - Job-Grenze: Fehler in den Job, nicht in den Loop
            logger.exception("atelier video failed: job=%s", job["job_id"])
            job["status"] = "failed"
            job["error"] = str(e)
            _write_job(project_id, job)


async def _poll_until_done(remote_id: str, *, key: str) -> str:
    """Pollt den Remote-Job bis completed; gibt die Video-URL zurück."""
    for _ in range(_MAX_POLLS):
        await asyncio.sleep(_POLL_INTERVAL)
        res = await poll_video_job(remote_id, key=key)
        status = res.get("status")
        if status == "completed":
            url = res.get("url")
            if not url:
                raise RuntimeError("Video fertig, aber keine URL geliefert.")
            return url
        if status == "failed":
            raise RuntimeError(res.get("error") or "Video-Generierung fehlgeschlagen.")
    raise RuntimeError("Zeitüberschreitung beim Warten auf das Video.")


def _source_to_data_url(project_id: str, source_rel: str) -> str | None:
    """Quell-Bild (Galerie) → data:-URL als Startframe. None wenn keins."""
    if not source_rel:
        return None
    from .service import file_to_data_url

    p = storage.safe_under(storage.atelier_root(project_id), source_rel)
    if p is None or not p.is_file():
        return None
    return file_to_data_url(p)
