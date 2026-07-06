"""Atelier — HTTP-Routen (/api/modules/atelier/*), projekt-scoped.

Jede Route verlangt ``require_auth`` UND Projekt-Mitgliedschaft
(``storage.user_can_access``). Bilder liegen im Projekt-Workspace und werden
vom Core über ``/api/files`` ausgeliefert; hier wird nur Metadata + Pfade
zurückgegeben. Referenzbilder werden für die Generierung als data:-URL
(base64) an die Image-API gereicht.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import characters, presets, screenplay, service, storage

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


# ---- Charaktere & CI --------------------------------------------------------

class CharacterIn(BaseModel):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    style_anchor: str = Field(default="", max_length=2000)
    palette: list[str] = Field(default_factory=list)
    seed: int | None = None
    model: str = Field(default="", max_length=200)


class CIIn(BaseModel):
    palette: list[str] = Field(default_factory=list)
    style_anchor: str = Field(default="", max_length=2000)
    default_model: str = Field(default="", max_length=200)
    aspect_ratio: str = Field(default="1:1", max_length=16)


@router.get("/projects/{project_id}/meta")
def get_meta(project_id: str, auth: Auth) -> dict:
    """Absoluter atelier-Root des Projekts — fürs Frontend zum Bauen von /api/files-URLs."""
    _guard(auth[0], project_id)
    return {"root": str(storage.atelier_root(project_id))}


@router.get("/projects/{project_id}/ci")
def get_ci(project_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return characters.get_ci(project_id)


@router.put("/projects/{project_id}/ci")
def put_ci(project_id: str, body: CIIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return characters.save_ci(project_id, body.model_dump())


@router.get("/projects/{project_id}/characters")
def list_characters(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return characters.list_characters(project_id)


@router.post("/projects/{project_id}/characters")
def create_character(project_id: str, body: CharacterIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return characters.create_character(project_id, body.model_dump())


@router.put("/projects/{project_id}/characters/{char_id}")
def update_character(project_id: str, char_id: str, body: CharacterIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    char = characters.update_character(project_id, char_id, body.model_dump())
    if char is None:
        raise coded(status.HTTP_404_NOT_FOUND, "character_not_found")
    return char


@router.delete("/projects/{project_id}/characters/{char_id}")
def delete_character(project_id: str, char_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not characters.delete_character(project_id, char_id):
        raise coded(status.HTTP_404_NOT_FOUND, "character_not_found")
    return {"ok": True}


_UPLOAD_STATUS = {
    "not_an_image": status.HTTP_400_BAD_REQUEST,
    "empty_file": status.HTTP_400_BAD_REQUEST,
    "file_too_large": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
}


@router.post("/projects/{project_id}/characters/{char_id}/upload")
async def upload_reference(project_id: str, char_id: str, file: UploadFile, auth: Auth) -> dict:
    """Lädt ein eigenes Bild hoch und hängt es als Hero-Referenz an die Figur."""
    _guard(auth[0], project_id)
    data = await file.read()
    try:
        char = characters.save_uploaded_reference(
            project_id, char_id, data, file.filename or "", file.content_type
        )
    except characters.UploadRejected as e:
        raise coded(_UPLOAD_STATUS.get(e.code, status.HTTP_400_BAD_REQUEST), e.code) from e
    if char is None:
        raise coded(status.HTTP_404_NOT_FOUND, "character_not_found")
    return char


# ---- Galerie ----------------------------------------------------------------

@router.get("/projects/{project_id}/gallery")
def list_gallery(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return service.scan_gallery(project_id)


class DeleteImageIn(BaseModel):
    rel: str = Field(max_length=300)


@router.post("/projects/{project_id}/gallery/delete")
def delete_image(project_id: str, body: DeleteImageIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not service.delete_gallery_image(project_id, body.rel):
        raise coded(status.HTTP_404_NOT_FOUND, "image_not_found")
    return {"ok": True}


# Video- und Film-Routen liegen in media_routes.py (eigener Router) — hält
# diese Datei schlank. Beide werden im Modul-register zusätzlich eingehängt.


# ---- Regie-Presets ----------------------------------------------------------

@router.get("/presets")
def get_presets(auth: Auth) -> dict:
    """Kamera-/Licht-/Wetter-Preset-Katalog {group: [keys]} für die Dropdowns."""
    return presets.catalog()


# ---- Generierung ------------------------------------------------------------

class GenerateIn(BaseModel):
    scene: str = Field(default="", max_length=4000)
    character_ids: list[str] = Field(default_factory=list)
    model: str = Field(default="", max_length=200)
    seed: int | None = None
    aspect_ratio: str = Field(default="", max_length=16)
    camera: dict[str, str] = Field(default_factory=dict)
    style: str = Field(default="", max_length=64)


@router.post("/projects/{project_id}/generate")
def post_generate(project_id: str, body: GenerateIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    from .generate import GenerateError

    try:
        return service.generate_for_project(project_id, body.model_dump())
    except GenerateError as e:
        # Externe Image-API-Fehler (400/Key/leer) als verständliche 422-Meldung
        # an den User durchreichen — nicht als nacktes internal_error/500.
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "generation_failed", message=str(e)) from e


# ---- Referenz hochladen / aus Output übernehmen -----------------------------

class PromoteIn(BaseModel):
    char_id: str
    rel: str = Field(max_length=300)


@router.post("/projects/{project_id}/promote")
def promote_reference(project_id: str, body: PromoteIn, auth: Auth) -> dict:
    """Übernimmt ein Galerie-Bild als Hero-Referenz einer Figur."""
    _guard(auth[0], project_id)
    src = storage.safe_under(storage.atelier_root(project_id), body.rel)
    if src is None or not src.is_file():
        raise coded(status.HTTP_404_NOT_FOUND, "image_not_found")
    rel = storage.save_reference_bytes(
        project_id, body.char_id, src.read_bytes(), ext=src.suffix.lstrip(".") or "png"
    )
    char = characters.add_reference(project_id, body.char_id, rel)
    if char is None:
        raise coded(status.HTTP_404_NOT_FOUND, "character_not_found")
    return char


# ---- Regie: Drehbuch-Kopf + Szenen (E1) -------------------------------------

class ScreenplayIn(BaseModel):
    title: str = Field(default="", max_length=200)
    logline: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=4000)
    film_model: str = Field(default="", max_length=200)
    audio_model: str = Field(default="", max_length=200)
    voice_model: str = Field(default="", max_length=200)
    aspect_ratio: str = Field(default="16:9", max_length=16)
    default_duration: int = Field(default=5, ge=1, le=60)
    scene_order: list[str] | None = None


class DialogueIn(BaseModel):
    character_id: str = Field(default="", max_length=32)
    line: str = Field(default="", max_length=2000)
    emotion: str = Field(default="", max_length=50)


class MusicIn(BaseModel):
    enabled: bool = False
    prompt: str = Field(default="", max_length=1000)
    music_rel: str | None = None


class SceneIn(BaseModel):
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    character_ids: list[str] = Field(default_factory=list)
    dialogues: list[DialogueIn] = Field(default_factory=list)
    music: MusicIn = Field(default_factory=MusicIn)
    camera: dict = Field(default_factory=dict)
    location: str = Field(default="", max_length=200)
    time_of_day: str = Field(default="", max_length=50)


class ReorderIn(BaseModel):
    scene_ids: list[str] = Field(default_factory=list)


@router.get("/projects/{project_id}/screenplay")
def get_screenplay_route(project_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return screenplay.get_screenplay(project_id)


@router.put("/projects/{project_id}/screenplay")
def put_screenplay_route(project_id: str, body: ScreenplayIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return screenplay.save_screenplay(project_id, body.model_dump(exclude_none=False))


@router.get("/projects/{project_id}/screenplay/scenes")
def list_scenes_route(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return screenplay.list_scenes(project_id)


@router.post("/projects/{project_id}/screenplay/scenes")
def create_scene_route(project_id: str, body: SceneIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return screenplay.create_scene(project_id, body.model_dump())


@router.put("/projects/{project_id}/screenplay/scenes/{scene_id}")
def update_scene_route(project_id: str, scene_id: str, body: SceneIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    updated = screenplay.update_scene(project_id, scene_id, body.model_dump())
    if updated is None:
        raise coded(status.HTTP_404_NOT_FOUND, "scene_not_found")
    return updated


@router.delete("/projects/{project_id}/screenplay/scenes/{scene_id}")
def delete_scene_route(project_id: str, scene_id: str, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    if not screenplay.delete_scene(project_id, scene_id):
        raise coded(status.HTTP_404_NOT_FOUND, "scene_not_found")
    return {"ok": True}


@router.post("/projects/{project_id}/screenplay/scenes/reorder")
def reorder_scenes_route(project_id: str, body: ReorderIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    return screenplay.reorder_scenes(project_id, body.scene_ids)
