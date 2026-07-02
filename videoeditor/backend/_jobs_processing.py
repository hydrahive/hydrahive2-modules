"""Video-Editor — Hintergrund-Verarbeitung für Import- und Export-Jobs.

Ausgelagert aus routes.py, damit die Route-Datei schlank bleibt (nur
HTTP-Dispatch). Läuft via asyncio.create_task, Fortschritt über den Job-Store.

WICHTIG: 'Import' erzeugt NUR Cache-Dateien (Proxy/Sprite/Meta) unter
videoeditor/ — das Original bleibt unangetastet an seinem Platz im
Projekt-Workspace (z.B. atelier/videos/..., oder woanders hochgeladen).
"""
from __future__ import annotations

import json

from . import _audio_peaks, _ffmpeg, storage
from ._jobstore import finish_job, set_progress
from .export_service import render_export
from .models import EDL, AudioMeta, VideoMeta
from .render_presets import OutputProfile

SPRITE_INTERVAL_SEC = 5.0
SPRITE_COLS = 10
SPRITE_TILE_W = 160
SPRITE_TILE_H = 90


async def process_import(project_id: str, source_rel: str, file_id: str, job_id: str) -> None:
    """Bereitet ein bestehendes Video im Projekt-Workspace für den Editor auf
    (Proxy/Keyframes/Sprite) — OHNE das Original zu kopieren oder zu verschieben."""
    jobs_dir = storage.jobs_dir(project_id)
    src = storage.source_path(project_id, source_rel)
    if src is None or not src.is_file():
        finish_job(jobs_dir, job_id, ok=False, error="Quelldatei nicht gefunden.")
        return
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
            file_id=file_id, filename=src.name, source_rel=source_rel,
            duration=info["duration"], fps=info["fps"], width=info["width"],
            height=info["height"], has_audio=info["has_audio"], keyframes=keyframes,
            sprite=sprite_meta, edl=EDL(file_id=file_id, timeline=[]),
        )
        storage.meta_path(project_id, file_id).write_text(
            meta.model_dump_json(indent=2), "utf-8"
        )
        finish_job(jobs_dir, job_id, ok=True)
    except _ffmpeg.FFmpegError as e:
        finish_job(jobs_dir, job_id, ok=False, error=str(e))


async def process_audio_prepare(
    project_id: str, source_rel: str, audio_id: str, job_id: str,
) -> None:
    """Bereitet eine Audiodatei aus dem Projekt-Workspace für die Nachvertonung
    auf: Dauer proben + Wellenform-Peaks berechnen. Original bleibt unangetastet
    (nur Sidecar-Meta + Peaks-JSON unter videoeditor/ werden geschrieben)."""
    jobs_dir = storage.jobs_dir(project_id)
    src = storage.source_path(project_id, source_rel)
    if src is None or not src.is_file():
        finish_job(jobs_dir, job_id, ok=False, error="Audiodatei nicht gefunden.")
        return
    try:
        info = await _ffmpeg.audio_probe(src)
        peaks = await _audio_peaks.compute_peaks(src, duration=info["duration"])
        storage.peaks_path(project_id, audio_id).write_text(
            json.dumps(peaks, ensure_ascii=False), "utf-8"
        )
        meta = AudioMeta(
            audio_id=audio_id, filename=src.name, source_rel=source_rel,
            duration=info["duration"], sample_rate=info["sample_rate"],
            channels=info["channels"],
        )
        storage.audio_meta_path(project_id, audio_id).write_text(
            meta.model_dump_json(indent=2), "utf-8"
        )
        finish_job(jobs_dir, job_id, ok=True)
    except _ffmpeg.FFmpegError as e:
        finish_job(jobs_dir, job_id, ok=False, error=str(e))


async def process_export(
    project_id: str, file_id: str, export_id: str, job_id: str,
    profile: OutputProfile | None = None,
) -> None:
    jobs_dir = storage.jobs_dir(project_id)
    try:
        meta_p = storage.meta_path(project_id, file_id)
        meta = VideoMeta.model_validate_json(meta_p.read_text("utf-8"))
        if not meta.edl or not meta.edl.timeline:
            raise _ffmpeg.FFmpegError("Keine Clips im EDL.")
        src = storage.source_path(project_id, meta.source_rel)
        if src is None or not src.is_file():
            raise _ffmpeg.FFmpegError("Original nicht gefunden.")
        dst = storage.export_path(project_id, export_id)
        source_meta = {"video_codec": None, "width": meta.width, "height": meta.height}

        async def on_progress(pct: float) -> None:
            set_progress(jobs_dir, job_id, int(pct * 100))

        await render_export(
            src, meta.edl.timeline, dst, keyframes=meta.keyframes,
            profile=profile, source_meta=source_meta, progress_cb=on_progress,
        )
        finish_job(jobs_dir, job_id, ok=True)
    except _ffmpeg.FFmpegError as e:
        finish_job(jobs_dir, job_id, ok=False, error=str(e))
