"""Video-Editor — API-Routen: Projekt-Videos browsen/importieren, EDL, Export.

Alle Endpunkte projekt-scoped (/projects/{project_id}/...), Zugriff nur für
Projekt-Mitglieder (storage.user_can_access). ffmpeg-Jobs laufen als
asyncio.create_task im Hintergrund (siehe _jobs_processing.py), Status via
Polling (Job-Store).

WICHTIG (Till, 2026-07-02): Originale bleiben IM Projekt-Workspace — der
Editor ist kein Silo. /browse listet alle Videos im ganzen Workspace (auch
z.B. atelier/videos/...), /import bereitet ein gewähltes Video auf (Proxy/
Keyframes), OHNE es zu kopieren. Direkter Upload bleibt für neue Dateien
möglich, landet aber sichtbar unter videoeditor/uploads/ im Projekt (Samba-
erreichbar), nicht in einem versteckten Ordner.
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import storage
from ._jobs_processing import process_export, process_import
from ._jobstore import new_job, read_job
from .models import EDL, VideoMeta

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


def _with_media_paths(project_id: str, meta: dict) -> dict:
    """Ergänzt absolute Pfade für Proxy/Sprite — der Browser lädt Medien über
    den zentralen /api/files-Endpoint (unterstützt ?token=), da <video>/<img>
    keinen Auth-Header senden können. Pfade werden LIVE berechnet, nicht in der
    Meta-JSON gespeichert (host-spezifisch → sonst Migrations-Problem)."""
    file_id = meta.get("file_id", "")
    meta["proxy_abs"] = str(storage.proxy_path(project_id, file_id))
    meta["sprite_abs"] = str(storage.sprite_path(project_id, file_id))
    return meta


# ---- Browsen: alle Videos im Projekt-Workspace --------------------------------

@router.get("/projects/{project_id}/browse")
def browse_project_videos(project_id: str, auth: Auth) -> list[dict]:
    """Alle Videodateien im GANZEN Projekt-Workspace (Atelier-Videos, eigene
    Uploads, was auch immer dort liegt) — mit Hinweis ob bereits importiert."""
    _guard(auth[0], project_id)
    root = storage.workspace_root(project_id)
    known = set(storage.list_known_file_ids(project_id))
    out = []
    for p in storage.list_project_videos(project_id):
        rel = str(p.relative_to(root))
        fid = storage.file_id_for(rel)
        out.append({
            "source_rel": rel,
            "filename": p.name,
            "file_id": fid,
            "imported": fid in known,
            "size_bytes": p.stat().st_size,
        })
    return out


@router.get("/projects/{project_id}/files")
def list_imported_files(project_id: str, auth: Auth) -> list[dict]:
    """Bereits importierte (aufbereitete) Videos — das ist die Editor-Bibliothek."""
    _guard(auth[0], project_id)
    out = []
    for file_id in storage.list_known_file_ids(project_id):
        meta_p = storage.meta_path(project_id, file_id)
        try:
            out.append(_with_media_paths(project_id, json.loads(meta_p.read_text("utf-8"))))
        except (json.JSONDecodeError, OSError):
            continue
    return out


@router.get("/projects/{project_id}/files/{file_id}")
def get_file_meta(project_id: str, file_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    meta_p = storage.meta_path(project_id, file_id)
    if not meta_p.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")
    return _with_media_paths(project_id, json.loads(meta_p.read_text("utf-8")))


# ---- Import (bestehendes Projekt-Video aufbereiten, async Job) --------------

class ImportIn(BaseModel):
    source_rel: str = Field(max_length=500)


@router.post("/projects/{project_id}/import")
async def import_video(project_id: str, body: ImportIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    src = storage.source_path(project_id, body.source_rel)
    if src is None or not src.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "source_not_found")
    file_id = storage.file_id_for(body.source_rel)
    job_id = storage.new_id()
    new_job(storage.jobs_dir(project_id), job_id, kind="import", file_id=file_id)
    asyncio.create_task(process_import(project_id, body.source_rel, file_id, job_id))
    return {"file_id": file_id, "job_id": job_id}


# ---- Upload (neue Datei, landet sichtbar unter videoeditor/uploads/) --------

@router.post("/projects/{project_id}/upload")
async def upload_video(project_id: str, auth: Auth, file: UploadFile = File(...)) -> dict:
    _guard(auth[0], project_id)
    ext = storage.video_ext_from(file.filename or "")
    if not ext:
        raise coded(status.HTTP_400_BAD_REQUEST, "unsupported_format")

    safe_name = f"{storage.new_id()}.{ext}"
    dst = storage.uploads_dir(project_id) / safe_name
    size = 0
    with dst.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > storage.MAX_UPLOAD_BYTES:
                out.close()
                dst.unlink(missing_ok=True)
                raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
            out.write(chunk)

    source_rel = str(dst.relative_to(storage.workspace_root(project_id)))
    file_id = storage.file_id_for(source_rel)
    job_id = storage.new_id()
    new_job(storage.jobs_dir(project_id), job_id, kind="import", file_id=file_id)
    asyncio.create_task(process_import(project_id, source_rel, file_id, job_id))
    return {"file_id": file_id, "job_id": job_id}


@router.get("/projects/{project_id}/jobs/{job_id}")
def get_job(project_id: str, job_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    job = read_job(storage.jobs_dir(project_id), job_id)
    if not job:
        raise coded(status.HTTP_404_NOT_FOUND, "job_not_found")
    return job


# ---- EDL (Schnitt speichern) --------------------------------------------------

@router.put("/projects/{project_id}/files/{file_id}/edl")
def save_edl(project_id: str, file_id: str, body: EDL, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    meta_p = storage.meta_path(project_id, file_id)
    if not meta_p.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")
    meta = VideoMeta.model_validate_json(meta_p.read_text("utf-8"))
    meta.edl = body.sanitized()
    meta_p.write_text(meta.model_dump_json(indent=2), "utf-8")
    return {"ok": True}


# ---- Export (async Job) -------------------------------------------------------

class ExportIn(BaseModel):
    filename: str = Field(default="export.mp4", max_length=200)


@router.post("/projects/{project_id}/files/{file_id}/export")
async def export_video(project_id: str, file_id: str, body: ExportIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not storage.meta_path(project_id, file_id).is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")
    export_id = storage.new_id()
    job_id = storage.new_id()
    new_job(storage.jobs_dir(project_id), job_id, kind="export", file_id=file_id)
    asyncio.create_task(process_export(project_id, file_id, export_id, job_id))
    return {"export_id": export_id, "job_id": job_id}


@router.get("/projects/{project_id}/exports/{export_id}")
def get_export_path(project_id: str, export_id: str, auth: Auth) -> dict:
    """Liefert den absoluten Export-Pfad — der Browser lädt/spielt ihn über
    /api/files (Token-Query). Konsistent mit Proxy/Sprite."""
    _guard(auth[0], project_id)
    p = storage.export_path(project_id, export_id)
    if not p.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "export_not_found")
    return {"export_abs": str(p)}
