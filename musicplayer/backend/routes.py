"""Musicplayer-Routen — /api/modules/musicplayer/[...].

- Liste + Streaming: jeder eingeloggte User (Streaming auch via ?token= fürs
  <audio>-Tag, das keinen Auth-Header setzen kann — Pattern aus core files.py).
- Upload + Delete: nur Admin.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from hydrahive.api.middleware.auth import (
    _decode,
    get_current_user_optional,
    require_admin,
    require_auth,
)
from hydrahive.api.middleware.errors import coded

from . import storage, tracks_store

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]
AdminAuth = Annotated[tuple[str, str], Depends(require_admin)]


@router.get("/tracks")
def list_tracks(_: Auth) -> list[dict]:
    return tracks_store.list_all()


@router.get("/tracks/{track_id}/stream")
def stream_track(
    track_id: int,
    user: Annotated[tuple[str, str] | None, Depends(get_current_user_optional)],
    token: str | None = Query(default=None),
) -> FileResponse:
    """Audio ausliefern. Auth via Bearer ODER ?token= (für <audio src>).

    FileResponse beantwortet Range-Requests selbst → Seeking im Player.
    """
    if user is None and token:
        payload = _decode(token)  # raised 401 bei invalid/expired
        user = (payload["sub"], payload["role"])
    if user is None:
        raise coded(status.HTTP_401_UNAUTHORIZED, "not_authenticated")

    track = tracks_store.get(track_id)
    if track is None:
        raise coded(status.HTTP_404_NOT_FOUND, "track_not_found")
    path = storage.file_path(track["filename"])
    if path is None:
        raise coded(status.HTTP_404_NOT_FOUND, "file_missing")
    return FileResponse(str(path), media_type="audio/mpeg", filename=f"{track['title']}.mp3")


@router.post("/tracks", status_code=status.HTTP_201_CREATED)
async def upload_track(
    auth: AdminAuth,
    file: UploadFile,
    title: str = Form(default=""),
) -> dict:
    admin, _ = auth
    if not storage.is_allowed_upload(file.filename or "", file.content_type):
        raise coded(status.HTTP_400_BAD_REQUEST, "not_an_mp3")

    data = await file.read()
    if len(data) == 0:
        raise coded(status.HTTP_400_BAD_REQUEST, "empty_file")
    if len(data) > storage.MAX_BYTES:
        raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")

    display = (title.strip() or (file.filename or "Track"))[:120]
    if display.lower().endswith(".mp3"):
        display = display[:-4]
    filename = storage.save_bytes(data)
    track_id = tracks_store.add(display, filename, len(data), admin)
    return {"id": track_id, "title": display, "size_bytes": len(data)}


@router.delete("/tracks/{track_id}")
def delete_track(track_id: int, _: AdminAuth) -> dict:
    filename = tracks_store.delete(track_id)
    if filename is None:
        raise coded(status.HTTP_404_NOT_FOUND, "track_not_found")
    storage.delete_file(filename)
    return {"ok": True}
