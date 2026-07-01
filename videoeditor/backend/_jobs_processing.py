"""Video-Editor — Hintergrund-Verarbeitung für Upload- und Export-Jobs.

Ausgelagert aus routes.py, damit die Route-Datei schlank bleibt (nur
HTTP-Dispatch). Läuft via asyncio.create_task, Fortschritt über den Job-Store.
"""
from __future__ import annotations

from . import _ffmpeg, storage
from ._jobstore import finish_job
from .export_service import render_export
from .models import EDL, VideoMeta

SPRITE_INTERVAL_SEC = 5.0
SPRITE_COLS = 10
SPRITE_TILE_W = 160
SPRITE_TILE_H = 90


async def process_upload(project_id: str, file_id: str, ext: str, filename: str, job_id: str) -> None:
    jobs_dir = storage.jobs_dir(project_id)
    src = storage.original_path(project_id, file_id, ext)
    try:
        info = await _ffmpeg.probe(src)
        keyframes = await _ffmpeg.keyframe_timestamps(src)
        proxy = storage.proxy_path(project_id, file_id)
        await _ffmpeg.make_proxy(src, proxy)
        sprite = storage.sprite_path(project_id, file_id)
        sprite_meta = await _ffmpeg.make_sprite(
            src, sprite, duration=info["duration"], interval=SPRITE_INTERVAL_SEC,
            cols=SPRITE_COLS, tile_w=SPRITE_TILE_W, tile_h=SPRITE_TILE_H,
        )
        meta = VideoMeta(
            file_id=file_id, filename=filename, duration=info["duration"],
            fps=info["fps"], width=info["width"], height=info["height"],
            has_audio=info["has_audio"], keyframes=keyframes, sprite=sprite_meta,
            edl=EDL(file_id=file_id, timeline=[]),
        )
        storage.meta_path(project_id, file_id).write_text(
            meta.model_dump_json(indent=2), "utf-8"
        )
        finish_job(jobs_dir, job_id, ok=True)
    except _ffmpeg.FFmpegError as e:
        finish_job(jobs_dir, job_id, ok=False, error=str(e))


async def process_export(project_id: str, file_id: str, export_id: str, job_id: str) -> None:
    jobs_dir = storage.jobs_dir(project_id)
    try:
        meta_p = storage.meta_path(project_id, file_id)
        meta = VideoMeta.model_validate_json(meta_p.read_text("utf-8"))
        if not meta.edl or not meta.edl.timeline:
            raise _ffmpeg.FFmpegError("Keine Clips im EDL.")
        src = next(
            (p for p in storage.list_originals(project_id) if p.stem == file_id), None,
        )
        if src is None:
            raise _ffmpeg.FFmpegError("Original nicht gefunden.")
        dst = storage.export_path(project_id, export_id)
        await render_export(src, meta.edl.timeline, dst, keyframes=meta.keyframes)
        finish_job(jobs_dir, job_id, ok=True)
    except _ffmpeg.FFmpegError as e:
        finish_job(jobs_dir, job_id, ok=False, error=str(e))
