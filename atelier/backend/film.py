"""Atelier — Film-Schnitt-Jobs (Clips zusammenfügen, asynchron via ffmpeg).

Mehrere Galerie-Clips in Reihenfolge → ein Film (lokal, keine API-Credits).
Async-Job-Muster wie video.py: start_film_job legt Job an + startet einen
Hintergrund-Task (ffmpeg-subprocess), schreibt Status in eine Job-Datei. Das
Frontend pollt die Liste.

Job-Store dateibasiert: atelier/films/<job_id>.json; Ergebnis films/<uuid>.mp4.
"""
from __future__ import annotations

import asyncio
import logging

from . import _ffmpeg, _jobstore, storage

logger = logging.getLogger("hhmod_atelier.film")

_SEM = asyncio.Semaphore(1)  # ffmpeg ist CPU-lastig → seriell
_RESOLUTIONS = {"16:9": (1280, 720), "9:16": (720, 1280), "1:1": (1080, 1080)}


def _write_job(project_id: str, job: dict) -> None:
    _jobstore.write_job(storage.films_dir(project_id), job)


def delete_film_job(project_id: str, job_id: str) -> bool:
    """Löscht einen Film-Job (JSON + fertige mp4). True bei Erfolg."""
    return _jobstore.delete_job(project_id, storage.films_dir(project_id), job_id, "film_rel")


def list_film_jobs(project_id: str) -> list[dict]:
    """Alle Film-Jobs des Projekts (neueste zuerst)."""
    return _jobstore.list_jobs(storage.films_dir(project_id))


def _resolve(project_id: str, rels: list[str]):
    """Validiert rel-Pfade gegen den atelier-Root. Gibt existierende Pfade zurück."""
    root = storage.atelier_root(project_id)
    out = []
    for rel in rels:
        p = storage.safe_under(root, rel)
        if p is not None and p.is_file():
            out.append(p)
    return out


def start_film_job(project_id: str, req: dict) -> dict:
    """Legt einen Film-Job an und startet den ffmpeg-Hintergrund-Task."""
    clips = [str(c) for c in (req.get("clips") or [])][:30]
    ratio = str(req.get("resolution") or "16:9")
    music_rel = str(req.get("music_rel") or "")
    job = {
        "job_id": storage.new_id(),
        "status": "pending",
        "clips": clips,
        "resolution": ratio if ratio in _RESOLUTIONS else "16:9",
        "music_rel": music_rel,
        "film_rel": None,
        "error": None,
        "created_at": _jobstore.now(),
    }
    _write_job(project_id, job)
    asyncio.create_task(_run_job(project_id, job))
    return job


async def _run_job(project_id: str, job: dict) -> None:
    async with _SEM:
        try:
            clips = _resolve(project_id, job["clips"])
            if len(clips) < 1:
                raise RuntimeError("Keine gültigen Clips ausgewählt.")
            music = None
            if job["music_rel"]:
                m = storage.safe_under(storage.atelier_root(project_id), job["music_rel"])
                music = m if (m and m.is_file()) else None

            job["status"] = "processing"
            _write_job(project_id, job)

            # Pro Clip: Audio vorhanden? + Dauer (für korrekten Ton-Erhalt im concat).
            clip_meta = [await _ffmpeg.probe_clip(c) for c in clips]

            w, h = _RESOLUTIONS[job["resolution"]]
            out_name = f"{storage.new_id()}.mp4"
            out_path = storage.films_dir(project_id) / out_name
            args = _ffmpeg.build_concat_command(
                clips, out_path, width=w, height=h, clip_meta=clip_meta, music=music
            )
            await _run_ffmpeg(args)

            if not out_path.is_file() or out_path.stat().st_size == 0:
                raise RuntimeError("ffmpeg lieferte keine Ausgabedatei.")
            job["status"] = "completed"
            job["film_rel"] = f"films/{out_name}"
            _write_job(project_id, job)
            logger.info("atelier film done: job=%s file=%s", job["job_id"], out_name)
        except Exception as e:  # noqa: BLE001 - Job-Grenze
            logger.exception("atelier film failed: job=%s", job["job_id"])
            job["status"] = "failed"
            job["error"] = str(e)
            _write_job(project_id, job)


async def _run_ffmpeg(args: list[str]) -> None:
    """Führt ffmpeg aus (ohne Shell). Wirft RuntimeError bei Exit != 0."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        tail = (stderr or b"").decode("utf-8", "replace")[-400:]
        raise RuntimeError(f"ffmpeg-Fehler (Exit {proc.returncode}): {tail}")
