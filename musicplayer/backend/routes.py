"""Projektgebundene Mediaplayer-API: Bibliothek, Upload, Stream und Löschen."""
from __future__ import annotations

import json
import logging
import re
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from pydantic import BaseModel

from . import storage, tracks_store
from .access import require_project_access, stream_principal
from .media_formats import MEDIA_FORMATS, MediaKind, extension

router = APIRouter(tags=["musicplayer"])
logger = logging.getLogger(__name__)
UPLOAD_LIMITS = {"audio": 50 * 1024 * 1024, "video": 60 * 1024 * 1024}


class TrackOut(BaseModel):
    id: int
    title: str
    size_bytes: int
    uploaded_by: str
    created_at: str
    media_kind: MediaKind
    ext: str
    meta: dict[str, Any]


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


def _meta(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _public(track: dict) -> TrackOut:
    values = {key: track[key] for key in TrackOut.model_fields if key != "meta"}
    return TrackOut(**values, meta=_meta(track.get("meta", "")))


def _download_filename(title: str, track_id: int, ext: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", title).strip(" ._")[:120]
    return f"{stem or f'track-{track_id}'}.{ext}"


@router.get("/projects/{project_id}/tracks", response_model=LibraryOut)
def list_tracks(
    project_id: str,
    principal: Annotated[AuthPrincipal, Depends(require_principal)],
    kind: Annotated[MediaKind | None, Query()] = None,
):
    access = require_project_access(project_id, principal, "read")
    tracks = tracks_store.list_all(project_id, kind)
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
    ext = extension(file.filename or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Dateiendung nicht unterstützt")
    media_kind = MEDIA_FORMATS[ext].kind
    limit = UPLOAD_LIMITS[media_kind]
    data = await file.read(limit + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Datei ist leer")
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"Datei zu groß (max. {limit // 1024 // 1024} MB)")

    clean_title = title.strip()[:200] or (file.filename or "Medium").rsplit(".", 1)[0][:200]
    filename = storage.save_bytes(project_id, data, ext=ext)
    try:
        track = tracks_store.add(
            project_id,
            title=clean_title,
            filename=filename,
            size_bytes=len(data),
            uploaded_by=principal.username,
            media_kind=media_kind,
            ext=ext,
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
        raise HTTPException(status_code=404, detail="Mediendatei nicht gefunden")

    ext = extension(path.name)
    disposition = "attachment" if download else "inline"
    filename = _download_filename(track["title"], track_id, ext)
    return FileResponse(
        path,
        media_type=MEDIA_FORMATS[ext].mime,
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
