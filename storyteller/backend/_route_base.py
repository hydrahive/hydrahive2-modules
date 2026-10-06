"""Storyteller — gemeinsame Bausteine der Routen (Auth, Projektprüfung, Fehlerabbildung)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from ._files import StoryError, is_project_id, user_can_access
from .storage import Conflict

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _guard(user: str, project_id: str) -> None:
    if not is_project_id(project_id) or not user_can_access(user, project_id):
        raise coded(status.HTTP_404_NOT_FOUND, "project_not_found")


def _call(fn, *args, **kw):
    try:
        return fn(*args, **kw)
    except Conflict as exc:
        return JSONResponse(status_code=409, content={"detail": {"code": "version_conflict", "current": exc.current}})
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc



def _set(m: BaseModel) -> dict:
    return {k: v for k, v in m.model_dump(exclude={"base_version"}).items() if v is not None}
