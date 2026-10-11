"""Tonstudio — REST unter /api/modules/tonstudio (SPEC.md §8).

Alle Projekt-Routen prüfen Mitgliedschaft (fremdes oder unbekanntes Projekt → 404). Die Modul-Freigabe
``module.tonstudio`` setzt der Kern beim Einhängen (api/main.py mount_module_routers).
"""
from __future__ import annotations

import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from hydrahive.api.middleware.auth import AuthPrincipal, require_auth, require_principal_or_query
from hydrahive.api.middleware.errors import coded

from . import generate, library, providers, songs, storage

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


def _check_sources(project_id: str, body: dict) -> None:
    """Jede Clip-Quelle muss im Projekt liegen (kein ``../``, kein absoluter Pfad)."""
    root = storage.workspace_root(project_id)
    for t in body.get("tracks") or []:
        for c in (t or {}).get("clips") or []:
            if storage.safe_under(root, str((c or {}).get("source_rel") or "")) is None:
                raise coded(status.HTTP_400_BAD_REQUEST, "source_outside_project")


def _song_or_404(project_id: str, song_id: str) -> dict:
    try:
        song = songs.get(project_id, song_id)
    except songs.SongFormatError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "song_format_unknown", message=str(e)) from e
    if song is None:
        raise coded(status.HTTP_404_NOT_FOUND, "song_not_found")
    return song


# ── Modelle ────────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(auth: Auth) -> list[dict]:
    return [m.to_dict() for m in await providers.list_models()]


# ── Songs ──────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/songs")
def list_songs(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return songs.list_songs(project_id)


@router.post("/projects/{project_id}/songs")
def create_song(project_id: str, body: dict, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    _check_sources(project_id, body)
    try:
        return songs.create(project_id, body)
    except ValidationError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_song", message=str(e)[:400]) from e


@router.get("/projects/{project_id}/songs/{song_id}")
def get_song(project_id: str, song_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return _song_or_404(project_id, song_id)


@router.put("/projects/{project_id}/songs/{song_id}")
def save_song(project_id: str, song_id: str, body: dict, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    _check_sources(project_id, body)
    _song_or_404(project_id, song_id)
    try:
        saved = songs.save(project_id, song_id, body, expected_version=int(body.get("expected_version") or 0))
    except songs.VersionConflict as e:
        raise coded(status.HTTP_409_CONFLICT, "version_conflict", current=e.current) from e
    except ValidationError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_song", message=str(e)[:400]) from e
    if saved is None:
        raise coded(status.HTTP_404_NOT_FOUND, "song_not_found")
    return saved


@router.delete("/projects/{project_id}/songs/{song_id}")
def trash_song(project_id: str, song_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not songs.trash(project_id, song_id):
        raise coded(status.HTTP_404_NOT_FOUND, "song_not_found")
    return {"ok": True}


@router.get("/projects/{project_id}/trash")
def list_trash(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return songs.list_trash(project_id)


@router.post("/projects/{project_id}/trash/{song_id}/restore")
def restore_song(project_id: str, song_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not songs.restore(project_id, song_id):
        raise coded(status.HTTP_404_NOT_FOUND, "song_not_found")
    return {"ok": True}


# ── Bibliothek ─────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/library")
def list_library(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return library.list_sources(project_id)


@router.post("/projects/{project_id}/library/upload")
async def upload(project_id: str, auth: Auth, file: UploadFile = File(...)) -> dict:
    _guard(auth[0], project_id)
    data = await file.read(storage.MAX_UPLOAD_BYTES + 1)
    try:
        return await library.add_upload(project_id, file.filename or "", data, user=auth[0])
    except library.UploadError as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "upload_rejected", message=str(e)) from e


class DeleteIn(BaseModel):
    source_rel: str = Field(min_length=1, max_length=500)


@router.post("/projects/{project_id}/library/delete")
def delete_clip(project_id: str, body: DeleteIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not library.delete_clip(project_id, body.source_rel):
        raise coded(status.HTTP_404_NOT_FOUND, "clip_not_found")
    return {"ok": True}


@router.get("/projects/{project_id}/file")
def get_file(
    project_id: str,
    who: Annotated[AuthPrincipal, Depends(require_principal_or_query)],
    rel: str = Query(min_length=1, max_length=500),
) -> FileResponse:
    """Audiodatei aus dem Projekt ausliefern (Player). Nur Audio-Endungen, nur innerhalb des Workspace.
    Nimmt auch ``?token=``, weil <audio> keinen Authorization-Header setzen kann."""
    _guard(who.username, project_id)
    path = storage.safe_under(storage.workspace_root(project_id), rel)
    if path is None or not path.is_file() or not storage.audio_ext(path.name):
        raise coded(status.HTTP_404_NOT_FOUND, "file_not_found")
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "audio/mpeg")


# ── Erzeugen ───────────────────────────────────────────────────────────────────

class GenerateIn(BaseModel):
    model: str = Field(min_length=1, max_length=200)
    request: dict = Field(default_factory=dict)


@router.post("/projects/{project_id}/generate")
async def post_generate(project_id: str, body: GenerateIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    try:
        return await generate.generate_clip(project_id, body.model, body.request, user=auth[0])
    except ValidationError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_request", message=str(e)[:400]) from e
    except providers.UnknownModel as e:
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_model", model=str(e)) from e
    except providers.ProviderError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "generation_failed", message=str(e)) from e
