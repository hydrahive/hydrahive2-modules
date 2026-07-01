"""Atelier — Audio-Routen (Musik-Generierung, Sound-Profile, Bibliothek).

Eigener Router (wie media_routes.py für Video/Film) unter demselben
/api/modules/atelier-Prefix. Musik-Generierung ist synchron (Lyria antwortet
in ~10-30s) — kein Job-Polling wie bei Video/Film nötig.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import audio_profiles, music, storage

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


# ---- Studio-Sound-Anker (CI-Kit-Erweiterung) --------------------------------

class MusicAnchorIn(BaseModel):
    music_style_anchor: str = Field(default="", max_length=2000)


@router.get("/projects/{project_id}/audio/anchor")
def get_anchor(project_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return {"music_style_anchor": audio_profiles.get_music_anchor(project_id)}


@router.put("/projects/{project_id}/audio/anchor")
def put_anchor(project_id: str, body: MusicAnchorIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return {"music_style_anchor": audio_profiles.save_music_anchor(project_id, body.music_style_anchor)}


# ---- Sound-Profile -----------------------------------------------------------

class ProfileIn(BaseModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    model: str = Field(default="", max_length=200)


@router.get("/projects/{project_id}/audio/profiles")
def list_profiles(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return audio_profiles.list_profiles(project_id)


@router.post("/projects/{project_id}/audio/profiles")
def create_profile(project_id: str, body: ProfileIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return audio_profiles.create_profile(project_id, body.model_dump())


@router.put("/projects/{project_id}/audio/profiles/{profile_id}")
def update_profile(project_id: str, profile_id: str, body: ProfileIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    profile = audio_profiles.update_profile(project_id, profile_id, body.model_dump())
    if profile is None:
        raise coded(status.HTTP_404_NOT_FOUND, "profile_not_found")
    return profile


@router.delete("/projects/{project_id}/audio/profiles/{profile_id}")
def delete_profile(project_id: str, profile_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not audio_profiles.delete_profile(project_id, profile_id):
        raise coded(status.HTTP_404_NOT_FOUND, "profile_not_found")
    return {"ok": True}


# ---- Bibliothek ---------------------------------------------------------------

@router.get("/projects/{project_id}/audio/library")
def list_library(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return music.scan_library(project_id)


class DeleteTrackIn(BaseModel):
    rel: str = Field(max_length=300)


@router.post("/projects/{project_id}/audio/library/delete")
def delete_track(project_id: str, body: DeleteTrackIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not music.delete_track(project_id, body.rel):
        raise coded(status.HTTP_404_NOT_FOUND, "track_not_found")
    return {"ok": True}


# ---- Generierung ----------------------------------------------------------------

class GenerateMusicIn(BaseModel):
    scene: str = Field(default="", max_length=4000)
    profile_ids: list[str] = Field(default_factory=list)
    model: str = Field(default="", max_length=200)


@router.post("/projects/{project_id}/audio/generate")
async def post_generate_music(project_id: str, body: GenerateMusicIn, auth: Auth) -> dict:
    # async: generate_music() ruft httpx im Streaming-Modus (SSE) auf.
    _guard(auth[0], project_id)
    try:
        return await music.generate_for_project(project_id, body.model_dump())
    except music.MusicError as e:
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "generation_failed", message=str(e)) from e
