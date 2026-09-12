"""Projektgebundene Musicplayer-API: Bibliothek, Upload, Stream/Download, Löschen."""
from __future__ import annotations

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hydrahive.api.middleware.auth import AuthPrincipal, require_principal

from . import storage, tracks_store
from .access import require_project_access, stream_principal

router = APIRouter(tags=["musicplayer"])
logger = logging.getLogger(__name__)
MAX_UPLOAD = 50 * 1024 * 1024


class TrackOut(BaseModel):
    id: int
    title: str
    size_bytes: int
    uploaded_by: str
    created_at: str


class PermissionsOut(BaseModel):
    can_upload: bool
    can_delete: bool


class LibraryOut(BaseModel):
    tracks: list[TrackOut]
    permissions: PermissionsOut


class CreatedOut(BaseModel):
    id: int
    title: str


class OkOut(BaseModel):
    ok: bool


def _public(track: dict) -> TrackOut:
    return TrackOut(**{key: track[key] for key in TrackOut.model_fields})


def _download_filename(title: str, track_id: int) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", title).strip(" ._")[:120]
    return f"{stem or f'track-{track_id}'}.mp3"


@router.get("/projects/{project_id}/tracks", response_model=LibraryOut)
def list_tracks(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
):
    access = require_project_access(project_id, principal, "read")
    tracks = tracks_store.list_all(project_id)
    # Lazy, sichere Übernahme aus dem bis v1.1 globalen Modulverzeichnis.
    for track in tracks:
        try:
            storage.file_path(project_id, track["filename"], expected_size=track["size_bytes"])
        except OSError as exc:
            logger.warning("Legacy-Audio %s konnte nicht migriert werden: %s", track["id"], exc)
    return LibraryOut(
        tracks=[_public(track) for track in tracks],
        permissions=PermissionsOut(
            can_upload=access.can_upload,
            can_delete=access.can_delete,
        ),
    )


@router.post(
    "/projects/{project_id}/tracks",
    response_model=CreatedOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_track(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()] = "",
):
    require_project_access(project_id, principal, "write")
    if not storage.is_allowed_upload(file.filename or "", file.content_type):
        raise HTTPException(status_code=400, detail="Nur MP3-Dateien erlaubt")

    data = await file.read(MAX_UPLOAD + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Datei ist leer")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="Datei zu groß (max. 50 MB)")

    clean_title = title.strip()[:200] or (file.filename or "Track").rsplit(".", 1)[0][:200]
    filename = storage.save_bytes(project_id, data)
    try:
        track = tracks_store.add(
            project_id,
            title=clean_title,
            filename=filename,
            size_bytes=len(data),
            uploaded_by=principal.username,
        )
    except Exception:
        storage.delete_file(project_id, filename)
        raise
    return CreatedOut(id=track["id"], title=track["title"])


@router.get("/projects/{project_id}/tracks/{track_id}/stream")
def stream_track(
    project_id: str,
    track_id: int,
    principal: Annotated[AuthPrincipal, Depends(stream_principal)],
    download: Annotated[bool, Query()] = False,
):
    require_project_access(project_id, principal, "read")
    track = tracks_store.get(project_id, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track nicht gefunden")
    path = storage.file_path(project_id, track["filename"], expected_size=track["size_bytes"])
    if path is None:
        raise HTTPException(status_code=404, detail="Audiodatei nicht gefunden")

    disposition = "attachment" if download else "inline"
    filename = _download_filename(track["title"], track_id)
    return FileResponse(
        path,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.delete("/projects/{project_id}/tracks/{track_id}", response_model=OkOut)
def delete_track(
    project_id: str,
    track_id: int,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
):
    require_project_access(project_id, principal, "admin")
    track = tracks_store.get(project_id, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track nicht gefunden")
    storage.delete_file(project_id, track["filename"])
    tracks_store.delete(project_id, track_id)
    return OkOut(ok=True)
