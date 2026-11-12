"""Routen des Ideen-Moduls — /api/modules/scratchpad.

Jede Route arbeitet nur mit den Ideen des angemeldeten Nutzers. Fremde Ideen
liefern 404, als gäbe es sie nicht. Herkunft, Task- und Board-Verweis lassen
sich über diese Routen nicht setzen.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from . import access, legacy_import, meta, notes, store, task_link

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]

_STATUS_CODES = {
    "project_not_found": status.HTTP_404_NOT_FOUND, "ideas_full": status.HTTP_409_CONFLICT,
    "task_already_linked": status.HTTP_409_CONFLICT, "tasks_not_installed": status.HTTP_409_CONFLICT,
}
_RAW_TITLE = store.MAX_TITLE * 2  # Leerraum wird erst im Speicher gekürzt, dort gilt die echte Grenze


def _fail(exc: store.IdeaError):
    return coded(_STATUS_CODES.get(exc.code, status.HTTP_422_UNPROCESSABLE_ENTITY), exc.code)


def _not_found():
    return coded(status.HTTP_404_NOT_FOUND, "idea_not_found")


def _detail(username: str, idea: dict) -> dict:
    public = {key: value for key, value in idea.items() if key != "username"}
    public["notes"] = notes.list_for(username, idea["id"])
    public["task"] = task_link.info(username, idea)
    return public


def _statuses(value: str) -> tuple[str, ...] | None:
    if value == "all":
        return None
    if value == "open":
        return store.OPEN_STATUSES
    if value in store.STATUSES:
        return (value,)
    raise coded(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_status")


class IdeaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=_RAW_TITLE)
    body: str = Field(default="", max_length=store.MAX_BODY)
    project_id: str | None = Field(default=None, max_length=64)


class IdeaUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=_RAW_TITLE)
    body: str | None = Field(default=None, max_length=store.MAX_BODY)
    status: str | None = Field(default=None, max_length=32)
    project_id: str | None = Field(default=None, max_length=64)


@router.get("/meta")
def get_meta(auth: Auth) -> dict:
    return meta.describe()


@router.get("/ideas")
def list_ideas(
    auth: Auth,
    project_id: Annotated[str | None, Query(max_length=64)] = None,
    status_filter: Annotated[str, Query(alias="status", max_length=32)] = "all",
) -> dict:
    user, _ = auth
    statuses = _statuses(status_filter)
    legacy_import.import_for(user)
    project = project_id or None
    return {
        "ideas": store.list_ideas(user, project=project, statuses=statuses),
        "counts": store.count_by_status(user, project=project),
    }


@router.post("/ideas", status_code=status.HTTP_201_CREATED)
def create_idea(auth: Auth, body: IdeaCreate) -> dict:
    user, role = auth
    try:
        project = access.check_project(user, role, body.project_id)
        idea = store.create(user, title=body.title, body=body.body, project_id=project)
    except store.IdeaError as exc:
        raise _fail(exc)
    return _detail(user, idea)


@router.get("/ideas/{idea_id}")
def get_idea(auth: Auth, idea_id: str) -> dict:
    user, _ = auth
    idea = store.get(user, idea_id)
    if idea is None:
        raise _not_found()
    return _detail(user, idea)


@router.patch("/ideas/{idea_id}")
def update_idea(auth: Auth, idea_id: str, body: IdeaUpdate) -> dict:
    user, role = auth
    if store.get(user, idea_id) is None:
        raise _not_found()
    sent = body.model_fields_set
    changes: dict = {}
    try:
        if "project_id" in sent:
            changes["project_id"] = access.check_project(user, role, body.project_id)
        for name in ("title", "body", "status"):
            if name in sent:
                changes[name] = getattr(body, name)
        idea = store.update(user, idea_id, **changes)
    except store.IdeaError as exc:
        raise _fail(exc)
    if idea is None:
        raise _not_found()
    return _detail(user, idea)


@router.post("/ideas/{idea_id}/task", status_code=status.HTTP_201_CREATED)
def create_task(auth: Auth, idea_id: str) -> dict:
    """Aus der Idee einen Task machen. Die Idee merkt sich den Task und steht danach auf „Geplant“."""
    user, _ = auth
    try:
        idea = task_link.create(user, idea_id)
    except store.IdeaError as exc:
        raise _fail(exc)
    if idea is None:
        raise _not_found()
    return _detail(user, idea)


@router.delete("/ideas/{idea_id}")
def delete_idea(auth: Auth, idea_id: str) -> dict:
    user, _ = auth
    if not store.delete(user, idea_id):
        raise _not_found()
    return {"removed": True}


@router.delete("/ideas/{idea_id}/notes/{note_id}")
def delete_note(auth: Auth, idea_id: str, note_id: int) -> dict:
    user, _ = auth
    if store.get(user, idea_id) is None:
        raise _not_found()
    if not notes.remove(user, idea_id, note_id):
        raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
    return {"removed": True}
