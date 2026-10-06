"""Storyteller — Routen für Szenen, Kapitel, Schnappschüsse und KI-Vorschläge."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import ai, snapshots, storage
from ._files import StoryError
from ._route_base import Auth, _call, _guard, _set

router = APIRouter()


class SceneIn(BaseModel):
    base_version: int
    text: str | None = None
    title: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=2000)
    pov: str | None = Field(default=None, max_length=200)
    status: str | None = Field(default=None, max_length=20)
    origin: str | None = Field(default=None, max_length=20)


class NewScene(BaseModel):
    chapter_id: str = Field(max_length=64)
    title: str = Field(default="", max_length=200)
    after: str | None = Field(default=None, max_length=64)


class NewChapter(BaseModel):
    part_id: str = Field(max_length=64)
    title: str = Field(max_length=200)
    scene_title: str = Field(max_length=200)


class SnapshotIn(BaseModel):
    text: str | None = None



class SuggestIn(BaseModel):
    scene_id: str = Field(max_length=64)
    action: Literal["rewrite", "expand", "shorten", "continue"]
    selection: str = Field(default="", max_length=ai.MAX_SELECTION)
    model: str | None = Field(default=None, max_length=200)


@router.post("/projects/{project_id}/books/{book_id}/scenes")
def add_scene(project_id: str, book_id: str, body: NewScene, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.add_scene, project_id, book_id, body.chapter_id, body.title, body.after)


@router.post("/projects/{project_id}/books/{book_id}/chapters")
def add_chapter(project_id: str, book_id: str, body: NewChapter, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.add_chapter, project_id, book_id, body.part_id, body.title, body.scene_title)


@router.put("/projects/{project_id}/books/{book_id}/scenes/{scene_id}")
def put_scene(project_id: str, book_id: str, scene_id: str, body: SceneIn, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.save_scene, project_id, book_id, scene_id, _set(body), body.base_version)


@router.delete("/projects/{project_id}/books/{book_id}/scenes/{scene_id}")
def delete_scene(project_id: str, book_id: str, scene_id: str, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.remove_scene, project_id, book_id, scene_id)


@router.get("/projects/{project_id}/books/{book_id}/scenes/{scene_id}/snapshots")
def get_snapshots(project_id: str, book_id: str, scene_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(storage.list_snapshots, project_id, book_id, scene_id)


@router.post("/projects/{project_id}/books/{book_id}/scenes/{scene_id}/snapshots")
def post_snapshot(project_id: str, book_id: str, scene_id: str, auth: Auth, body: SnapshotIn | None = None):
    _guard(auth, project_id)
    return _call(snapshots.add_snapshot, project_id, book_id, scene_id, body.text if body else None)


@router.get("/projects/{project_id}/books/{book_id}/scenes/{scene_id}/snapshots/{snapshot_id}")
def get_snapshot(project_id: str, book_id: str, scene_id: str, snapshot_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(snapshots.get_snapshot, project_id, book_id, scene_id, snapshot_id)


@router.post("/projects/{project_id}/books/{book_id}/ai/suggest")
async def ai_suggest(project_id: str, book_id: str, body: SuggestIn, auth: Auth):
    _guard(auth, project_id)
    if body.action != "continue" and not body.selection.strip():
        raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "selection_required")
    try:
        return await ai.suggest(auth[0], project_id, book_id, body.scene_id, body.action, body.selection, body.model)
    except ai.AiError as exc:
        return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message}})
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
