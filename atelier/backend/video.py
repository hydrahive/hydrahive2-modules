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
import time

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
# Timeout dauer-abhängig: langsame Premium-Modelle (Sora 2 Pro, Veo) brauchen für
# lange Clips deutlich länger als die alte feste 7,5-min-Grenze. Basis + Zuschlag
# pro Sekunde Videolänge. Beispiel: 20s-Video → 15min + 20*45s = 30 min.
_POLL_TIMEOUT_BASE = 900.0      # 15 min Grundbudget
_POLL_TIMEOUT_PER_SEC = 45.0    # + pro Sekunde angeforderter Videolänge
_POLL_TIMEOUT_CAP = 2700.0      # harte Obergrenze 45 min
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


async def render_clip(
    project_id: str, *, source_rel: str, prompt: str, model: str,
    duration: int = 5, aspect_ratio: str = "16:9",
) -> str:
    """Rendert EINEN Clip synchron (await-bar): submit → poll → download.

    Gibt den ``videos/<name>``-rel zurück. Wirft bei Fehler (Aufrufer behandelt).
    Ohne eigene Job-Datei — für Orchestrierung (E5 Batch-Render) wiederverwendbar.
    Teilt sich das Semaphor mit den normalen Video-Jobs (Rate-Limit-Schutz).
    """
    async with _SEM:
        key = openrouter_key()
        if not key:
            raise RuntimeError("Kein OpenRouter-API-Key konfiguriert.")
        image_url = _source_to_data_url(project_id, source_rel) if source_rel else None
        model = model.strip() or _DEFAULT_MODEL
        remote_id = await _submit_image_to_video(
            prompt=prompt, model=model, key=key,
            duration=_clamp_duration(model, duration), aspect_ratio=aspect_ratio,
            image_url=image_url,
        )
        url = await _poll_until_done(remote_id, key=key, duration=duration)
        path = await download_video(url, storage.videos_dir(project_id), key=key)
        return f"videos/{path.name}"


async def _run_job(project_id: str, job: dict) -> None:
    """Hintergrund-Task: nutzt render_clip (hält das Semaphor selbst), schreibt Status."""
    try:
        job["status"] = "processing"
        _write_job(project_id, job)
        rel = await render_clip(
            project_id, source_rel=job["source_rel"], prompt=job["prompt"],
            model=job["model"], duration=job["duration"], aspect_ratio=job["aspect_ratio"],
        )
        job["status"] = "completed"
        job["video_rel"] = rel
        _write_job(project_id, job)
        logger.info("atelier video done: job=%s file=%s", job["job_id"], rel)
    except Exception as e:  # noqa: BLE001 - Job-Grenze: Fehler in den Job, nicht in den Loop
        logger.exception("atelier video failed: job=%s", job["job_id"])
        job["status"] = "failed"
        job["error"] = str(e)
        _write_job(project_id, job)


def _poll_timeout_for(duration: int) -> float:
    """Zeitbudget fürs Pollen — länger für längere Clips (langsame Modelle)."""
    try:
        secs = max(1, int(duration))
    except (TypeError, ValueError):
        secs = 5
    return min(_POLL_TIMEOUT_CAP, _POLL_TIMEOUT_BASE + secs * _POLL_TIMEOUT_PER_SEC)


async def _poll_until_done(remote_id: str, *, key: str, duration: int = 5) -> str:
    """Pollt den Remote-Job bis completed; gibt die Video-URL zurück.

    Zeitbasierter Timeout (dauer-abhängig) statt fester Poll-Anzahl — Sora 2 Pro
    & Veo brauchen für lange Clips >7,5 min.
    """
    deadline = time.monotonic() + _poll_timeout_for(duration)
    while time.monotonic() < deadline:
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
    raise RuntimeError(
        "Zeitüberschreitung beim Warten auf das Video. Lange/teure Modelle "
        "(z.B. Sora 2 Pro bei 20s) können sehr lange dauern — bitte erneut versuchen "
        "oder ein schnelleres Modell / kürzere Dauer wählen."
    )


async def extract_continuation_frame(project_id: str, video_rel: str) -> str | None:
    """Letzten Frame eines Videos als Galerie-Bild speichern (für Fortsetzungen).

    Gibt den images/-rel des neuen Bildes zurück, oder None wenn das Video fehlt.
    """
    from .service import write_image_sidecar
    src = storage.safe_under(storage.atelier_root(project_id), video_rel)
    if src is None or not src.is_file():
        return None
    name = storage.make_media_name("Fortsetzung letzter Frame", ext="jpg")
    out = storage.images_dir(project_id) / name
    try:
        await _ffmpeg.extract_last_frame(src, out)
    except Exception:
        out.unlink(missing_ok=True)
        raise
    rel = f"images/{name}"
    write_image_sidecar(project_id, rel, {"prompt": "(Fortsetzung – letzter Frame)", "scene": ""})
    return rel


def _source_to_data_url(project_id: str, source_rel: str) -> str | None:
    """Quell-Bild (Galerie) → data:-URL als Startframe. None wenn keins."""
    if not source_rel:
        return None
    from .service import file_to_data_url

    p = storage.safe_under(storage.atelier_root(project_id), source_rel)
    if p is None or not p.is_file():
        return None
    return file_to_data_url(p)
