"""Atelier — HTTP-Routen (/api/modules/atelier/*), projekt-scoped.

Jede Route verlangt ``require_auth`` UND Projekt-Mitgliedschaft
(``storage.user_can_access``). Bilder liegen im Projekt-Workspace und werden
vom Core über ``/api/files`` ausgeliefert; hier wird nur Metadata + Pfade
zurückgegeben. Referenzbilder werden für die Generierung als data:-URL
(base64) an die Image-API gereicht.
"""
from __future__ import annotations

import base64
import json
import mimetypes
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import characters, storage

router = APIRouter()
Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not storage.is_project_id(project_id) or not storage.user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


def _abs_path(project_id: str, rel: str) -> str:
    """Absoluter Pfad einer Atelier-Datei (für /api/files-URLs im Frontend)."""
    return str(storage.atelier_root(project_id) / rel)


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


# ---- Galerie ----------------------------------------------------------------

@router.get("/projects/{project_id}/gallery")
def list_gallery(project_id: str, auth: Auth) -> list[dict]:
    _guard(auth[0], project_id)
    return _scan_gallery(project_id)


def _scan_gallery(project_id: str) -> list[dict]:
    out_dir = storage.output_dir(project_id)
    items: list[dict] = []
    for img in out_dir.iterdir():
        if img.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            continue
        meta_path = img.with_suffix(img.suffix + ".json")
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = {}
        items.append({
            "name": img.name,
            "path": str(img),
            "rel": f"output/{img.name}",
            "created_at": meta.get("created_at"),
            "prompt": meta.get("prompt"),
            "seed": meta.get("seed"),
            "model": meta.get("model"),
            "mtime": img.stat().st_mtime,
        })
    items.sort(key=lambda i: i["mtime"], reverse=True)
    return items


# ---- Generierung ------------------------------------------------------------

class GenerateIn(BaseModel):
    scene: str = Field(default="", max_length=4000)
    character_ids: list[str] = Field(default_factory=list)
    model: str = Field(default="", max_length=200)
    seed: int | None = None
    aspect_ratio: str = Field(default="", max_length=16)


@router.post("/projects/{project_id}/generate")
def post_generate(project_id: str, body: GenerateIn, auth: Auth) -> dict:
    _guard(auth[0], project_id)
    from . import service
    return service.generate_for_project(project_id, body.model_dump())


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


def file_to_data_url(path) -> str:
    """Lokale Bilddatei → data:-URL (base64) für input_references der Image-API."""
    mime, _ = mimetypes.guess_type(str(path))
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime or 'image/png'};base64,{b64}"
