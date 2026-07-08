"""Atelier — Media-Job-Routen (Video + Film, async).

Eigener Router für die lang laufenden Media-Jobs (Image-to-Video und
Film-Schnitt), ausgelagert aus routes.py um diese schlank zu halten. Wird vom
Modul über register_router zusätzlich eingehängt — gleicher /api/modules/atelier
Prefix, daher dieselben /projects/{id}/...-Pfade.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import film, storage, video

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


# ---- Video (Image-to-Video) -------------------------------------------------

class VideoIn(BaseModel):
    source_rel: str = Field(default="", max_length=300)  # leer = Text-to-Video
    end_source_rel: str = Field(default="", max_length=300)  # optionales Endbild (last_frame)
    prompt: str = Field(default="", max_length=2000)
    model: str = Field(default="", max_length=200)
    duration: int = Field(default=5, ge=1, le=20)
    aspect_ratio: str = Field(default="16:9", max_length=16)


@router.get("/projects/{project_id}/videos")
def list_videos(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return video.list_video_jobs(project_id)


@router.delete("/projects/{project_id}/videos/{job_id}")
def delete_video(project_id: str, job_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not video.delete_video_job(project_id, job_id):
        raise coded(status.HTTP_404_NOT_FOUND, "video_not_found")
    return {"ok": True}


class ContinueIn(BaseModel):
    video_rel: str = Field(max_length=300)


@router.post("/projects/{project_id}/videos/continue")
async def continue_frame(project_id: str, body: ContinueIn, auth: Auth) -> dict:
    """Extrahiert den letzten Frame eines Videos als neues Galerie-Bild.
    Damit lässt sich ein Anschluss-Clip erzeugen (nahtlose Fortsetzung)."""
    _guard(auth[0], project_id)
    rel = await video.extract_continuation_frame(project_id, body.video_rel)
    if rel is None:
        raise coded(status.HTTP_404_NOT_FOUND, "video_not_found")
    return {"rel": rel, "path": str(storage.atelier_root(project_id) / rel)}


@router.post("/projects/{project_id}/videos")
async def create_video(project_id: str, body: VideoIn, auth: Auth) -> dict:
    # async, damit start_video_job() einen laufenden Event-Loop für
    # asyncio.create_task hat (sync-Routen laufen im Thread-Pool ohne Loop).
    _guard(auth[0], project_id)
    # Startbild ist optional: mit source_rel = Image-to-Video, ohne = Text-to-Video.
    if body.source_rel:
        src = storage.safe_under(storage.atelier_root(project_id), body.source_rel)
        if src is None or not src.is_file():
            raise coded(status.HTTP_404_NOT_FOUND, "image_not_found")
    elif not body.prompt.strip():
        # Ohne Bild MUSS ein Prompt da sein (sonst hat das Modell keine Vorlage).
        raise coded(status.HTTP_400_BAD_REQUEST, "prompt_required")
    # Endbild (last_frame) nur zulassen, wenn es auch ein Startbild gibt und die
    # Datei existiert — sonst ignorieren.
    if body.end_source_rel:
        if not body.source_rel:
            raise coded(status.HTTP_400_BAD_REQUEST, "end_image_needs_start")
        end = storage.safe_under(storage.atelier_root(project_id), body.end_source_rel)
        if end is None or not end.is_file():
            raise coded(status.HTTP_404_NOT_FOUND, "end_image_not_found")
    return video.start_video_job(project_id, body.model_dump())


# ---- Film-Schnitt (Clips zusammenfügen, ffmpeg) -----------------------------

class FilmIn(BaseModel):
    clips: list[str] = Field(default_factory=list)
    resolution: str = Field(default="16:9", max_length=8)
    music_rel: str = Field(default="", max_length=300)


@router.get("/projects/{project_id}/films")
def list_films(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return film.list_film_jobs(project_id)


@router.delete("/projects/{project_id}/films/{job_id}")
def delete_film(project_id: str, job_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not film.delete_film_job(project_id, job_id):
        raise coded(status.HTTP_404_NOT_FOUND, "film_not_found")
    return {"ok": True}


@router.post("/projects/{project_id}/films")
async def create_film(project_id: str, body: FilmIn, auth: Auth) -> dict:
    # async wegen asyncio.create_task im Job-Start (wie create_video).
    _guard(auth[0], project_id)
    if len(body.clips) < 1:
        raise coded(status.HTTP_400_BAD_REQUEST, "no_clips")
    return film.start_film_job(project_id, body.model_dump())
