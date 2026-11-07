"""Project workspace API: design documents and the embedded agent chat."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_principal
from hydrahive.api.middleware.errors import coded
from hydrahive.api.routes._project_route_helpers import check_project_access
from pydantic import BaseModel, ConfigDict, Field

from . import chat, design_docs, projects

router = APIRouter()
Principal = Annotated[AuthPrincipal, Depends(require_principal)]

_NOT_FOUND = {"game_studio_design_not_found"}
_CONFLICT = {"game_studio_design_conflict", "game_studio_design_exists", "game_studio_design_symlink",
             "game_studio_design_escape", "game_studio_design_limit"}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DocSave(_Strict):
    content: str = Field(max_length=design_docs.MAX_BYTES)
    etag: str | None = Field(default=None, max_length=64)


class DocCreate(_Strict):
    title: str = Field(min_length=1, max_length=120)


def _config(project_id: str, principal: AuthPrincipal, required: str) -> dict:
    found = projects.get(project_id)
    if found is None:
        raise coded(status.HTTP_404_NOT_FOUND, "game_studio_project_not_found")
    config, _project = found
    check_project_access(config, principal.username, principal.role, required=required)
    return config


def _can_write(config: dict, principal: AuthPrincipal) -> bool:
    try:
        check_project_access(config, principal.username, principal.role, required="write")
    except HTTPException:
        return False
    return True


def _doc_error(exc: design_docs.DesignDocError) -> None:
    code = str(exc)
    if code in _NOT_FOUND:
        raise coded(status.HTTP_404_NOT_FOUND, code)
    if code in _CONFLICT:
        raise coded(status.HTTP_409_CONFLICT, code)
    if code == "game_studio_design_too_large":
        raise coded(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, code)
    raise coded(status.HTTP_400_BAD_REQUEST, code)


@router.get("/projects/{project_id}/design")
def list_design(project_id: str, principal: Principal) -> dict:
    config = _config(project_id, principal, "read")
    can_write = _can_write(config, principal)
    try:
        if can_write:
            design_docs.ensure_starters(project_id)
        return {"docs": design_docs.list_docs(project_id), "can_write": can_write}
    except design_docs.DesignDocError as exc:
        _doc_error(exc)


@router.get("/projects/{project_id}/design/{slug}")
def get_design(project_id: str, slug: str, principal: Principal) -> dict:
    _config(project_id, principal, "read")
    try:
        return design_docs.get_doc(project_id, slug)
    except design_docs.DesignDocError as exc:
        _doc_error(exc)


@router.put("/projects/{project_id}/design/{slug}")
def save_design(project_id: str, slug: str, body: DocSave, principal: Principal) -> dict:
    _config(project_id, principal, "write")
    try:
        return design_docs.save_doc(project_id, slug, body.content, body.etag)
    except design_docs.DesignDocError as exc:
        _doc_error(exc)


@router.post("/projects/{project_id}/design", status_code=status.HTTP_201_CREATED)
def create_design(project_id: str, body: DocCreate, principal: Principal) -> dict:
    _config(project_id, principal, "write")
    try:
        return design_docs.create_doc(project_id, body.title)
    except design_docs.DesignDocError as exc:
        _doc_error(exc)


@router.get("/projects/{project_id}/chat")
def chat_info(project_id: str, principal: Principal) -> dict:
    config = _config(project_id, principal, "read")
    return chat.info(config, _can_write(config, principal))


@router.post("/projects/{project_id}/chat")
def chat_start(project_id: str, principal: Principal) -> dict:
    config = _config(project_id, principal, "write")
    started = chat.start(config, principal.username)
    if started is None:
        raise coded(status.HTTP_409_CONFLICT, "project_agent_missing")
    return started
