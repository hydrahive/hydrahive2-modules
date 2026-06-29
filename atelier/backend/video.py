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
import logging

import httpx

from hydrahive.llm._config import openrouter_key
from hydrahive.tools._openrouter_video import download_video, poll_video_job

from . import _ffmpeg, _jobstore, storage

logger = logging.getLogger("hhmod_atelier.video")

_VIDEOS_URL = "https://openrouter.ai/api/v1/videos"

_DEFAULT_MODEL = "minimax/hailuo-2.3"
# Erlaubte Dauern je Modell (OpenRouter lehnt andere mit HTTP 400 ab).
# Erster Wert = Default/Fallback. Unbekannte Modelle: keine Korrektur.
_MODEL_DURATIONS: dict[str, list[int]] = {
    "minimax/hailuo-2.3": [6, 10],
    "kwaivgi/kling-v3.0-std": [5, 10],
    "bytedance/seedance-2.0-fast": [5, 10],
}
_POLL_INTERVAL = 5.0
_MAX_POLLS = 90  # ~7,5 min Obergrenze
_SEM = asyncio.Semaphore(2)  # max 2 parallele Video-Jobs


def _write_job(project_id: str, job: dict) -> None:
    _jobstore.write_job(storage.videos_dir(project_id), job)


def delete_video_job(project_id: str, job_id: str) -> bool:
    """Löscht einen Video-Job (JSON + fertige mp4). True bei Erfolg."""
    return _jobstore.delete_job(project_id, storage.videos_dir(project_id), job_id, "video_rel")


def list_video_jobs(project_id: str) -> list[dict]:
    """Alle Video-Jobs des Projekts (neueste zuerst)."""
    return _jobstore.list_jobs(storage.videos_dir(project_id))


def _clamp_duration(model: str, duration: int) -> int:
    """Zieht die Dauer auf einen vom Modell erlaubten Wert (sonst HTTP 400)."""
    allowed = _MODEL_DURATIONS.get(model)
    if not allowed or duration in allowed:
        return duration
    # nächstgelegener erlaubter Wert
    return min(allowed, key=lambda a: abs(a - duration))


def start_video_job(project_id: str, req: dict) -> dict:
    """Legt einen Video-Job an und startet den Hintergrund-Task. Gibt den Job zurück."""
    job_id = storage.new_id()
    source_rel = str(req.get("source_rel") or "")
    model = str(req.get("model") or "").strip() or _DEFAULT_MODEL
    duration = _clamp_duration(model, int(req.get("duration") or 5))
    job = {
        "job_id": job_id,
        "status": "pending",
        "source_rel": source_rel,
        "prompt": str(req.get("prompt") or "")[:2000],
        "model": model,
        "duration": duration,
        "aspect_ratio": str(req.get("aspect_ratio") or "16:9")[:16],
        "video_rel": None,
        "error": None,
        "created_at": _jobstore.now(),
    }
    _write_job(project_id, job)
    asyncio.create_task(_run_job(project_id, job))
    return job


async def _submit_image_to_video(
    *, prompt: str, model: str, key: str, duration: int,
    aspect_ratio: str, image_url: str | None,
) -> str:
    """Startet einen Video-Job. Gibt job_id zurück.

    Schickt das Startbild als ``frame_images`` mit ``frame_type=first_frame`` —
    das ist das von OpenRouter erwartete Image-to-Video-Format. (Das flache
    ``image_url`` aus dem Core-Tool wird von der Video-API ignoriert → das Modell
    macht stattdessen Text-to-Video, daher drifteten Figur+Szene komplett weg.)
    """
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
    }
    if image_url:
        payload["frame_images"] = [{
            "type": "image_url",
            "image_url": {"url": image_url},
            "frame_type": "first_frame",
        }]
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _VIDEOS_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"OpenRouter Video-Submit Fehler {resp.status_code}: {resp.text[:400]}")
            data = resp.json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Netzwerk-Fehler beim Video-Submit: {e}") from e
    job_id = data.get("id") or data.get("job_id") or ""
    if not job_id:
        raise RuntimeError(f"Kein job_id in OpenRouter-Antwort: {str(data)[:200]}")
    return str(job_id)


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

            remote_id = await _submit_image_to_video(
                prompt=job["prompt"], model=job["model"], key=key,
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


async def extract_continuation_frame(project_id: str, video_rel: str) -> str | None:
    """Letzten Frame eines Videos als Galerie-Bild speichern (für Fortsetzungen).

    Gibt den output/-rel des neuen Bildes zurück, oder None wenn das Video fehlt.
    """
    from .service import write_image_sidecar
    src = storage.safe_under(storage.atelier_root(project_id), video_rel)
    if src is None or not src.is_file():
        return None
    tmp = storage.output_dir(project_id) / f"{storage.new_id()}.jpg"
    await _ffmpeg.extract_last_frame(src, tmp)
    write_image_sidecar(project_id, tmp.name, {"prompt": "(Fortsetzung – letzter Frame)", "scene": ""})
    return f"output/{tmp.name}"


def _source_to_data_url(project_id: str, source_rel: str) -> str | None:
    """Quell-Bild (Galerie) → data:-URL als Startframe. None wenn keins."""
    if not source_rel:
        return None
    from .service import file_to_data_url

    p = storage.safe_under(storage.atelier_root(project_id), source_rel)
    if p is None or not p.is_file():
        return None
    return file_to_data_url(p)
