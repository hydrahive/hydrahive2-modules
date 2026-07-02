"""Video-Editor — Audio-Nachvertonung-Routen (SPEC-AUDIO.md).

Projekt-scoped wie der übrige Editor (kein Admin-only): browst Audiodateien im
Projekt-Workspace (generierte Musik/Sprache + sonstige), bereitet sie async auf
(Dauer + Wellenform-Peaks) und liefert Meta/Peaks. Originale bleiben unangetastet
im Workspace; nur Sidecar-Meta + Peaks-JSON landen unter videoeditor/.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import storage
from ._deps import Auth, guard
from ._jobs_processing import process_audio_prepare
from ._jobstore import new_job

router = APIRouter()


@router.get("/projects/{project_id}/audio/browse")
def browse_project_audio(project_id: str, auth: Auth) -> list[dict]:
    """Alle Audiodateien im Projekt-Workspace (generierte Musik/Sprache unter
    generated/ + sonstige) — mit Hinweis, ob bereits aufbereitet."""
    guard(auth[0], project_id)
    root = storage.workspace_root(project_id)
    known = set(storage.list_known_audio_ids(project_id))
    out = []
    for p in storage.list_project_audio(project_id):
        rel = str(p.relative_to(root))
        aid = storage.file_id_for(rel)
        out.append({
            "source_rel": rel,
            "filename": p.name,
            "audio_id": aid,
            "prepared": aid in known,
            "size_bytes": p.stat().st_size,
        })
    return out


class AudioPrepareIn(BaseModel):
    source_rel: str = Field(max_length=500)


@router.post("/projects/{project_id}/audio/prepare")
async def prepare_audio(project_id: str, body: AudioPrepareIn, auth: Auth) -> dict:
    """Dauer proben + Wellenform-Peaks vorberechnen (async Job)."""
    guard(auth[0], project_id)
    src = storage.source_path(project_id, body.source_rel)
    if src is None or not src.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "source_not_found")
    if storage.audio_ext_from(src.name) is None:
        raise coded(status.HTTP_400_BAD_REQUEST, "unsupported_format")
    audio_id = storage.file_id_for(body.source_rel)
    job_id = storage.new_id()
    new_job(storage.jobs_dir(project_id), job_id, kind="audio_prepare", file_id=audio_id)
    asyncio.create_task(process_audio_prepare(project_id, body.source_rel, audio_id, job_id))
    return {"audio_id": audio_id, "job_id": job_id}


@router.get("/projects/{project_id}/audio/{audio_id}")
def get_audio_meta(project_id: str, audio_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    meta_p = storage.audio_meta_path(project_id, audio_id)
    if not meta_p.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "audio_not_found")
    meta = json.loads(meta_p.read_text("utf-8"))
    meta["peaks_abs"] = str(storage.peaks_path(project_id, audio_id))
    return meta


@router.get("/projects/{project_id}/audio/{audio_id}/peaks")
def get_audio_peaks(project_id: str, audio_id: str, auth: Auth) -> dict:
    guard(auth[0], project_id)
    peaks_p = storage.peaks_path(project_id, audio_id)
    if not peaks_p.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "peaks_not_found")
    return json.loads(peaks_p.read_text("utf-8"))
