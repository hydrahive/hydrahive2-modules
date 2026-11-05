"""Schnittstellen /api/modules/vibe (PLAN-V1.md). Nur Admins, nur eigene Projekte.

Klein gehalten: Zustand, Projekt anlegen/löschen, Chat öffnen, Versionen ansehen, Zurück, „Nochmal“, Heilung an/aus.
Fehler kommen als Code (`vibe_…`), nie als Text mit Pfaden. Das Modell kommt vom System (Standardmodell), nicht vom Nutzer.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import chat, container, idle, incus, jobs, projects, state, version_text, versions

logger = logging.getLogger(__name__)
router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]
_tasks: set[asyncio.Task] = set()                    # starke Verweise, sonst räumt Python laufende Aufträge weg


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


class NewProject(BaseModel):
    model_config = ConfigDict(extra="ignore")                    # ein mitgeschicktes `model` wird bewusst ignoriert
    name: str = Field(min_length=1, max_length=projects.MAX_NAME)


class HealSwitch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    enabled: bool


def _own(pid: str, p: AuthPrincipal) -> dict:
    row = state.get_row(pid)
    if row is None or row["owner"] != p.username:
        raise coded(status.HTTP_404_NOT_FOUND, "vibe_project_not_found")
    return row


def _default_model() -> str:
    from hydrahive.llm.client import default_model
    return default_model()


async def _background(coro) -> None:
    try:
        await coro
    except (jobs.JobError, projects.VibeProjectError, container.VibeError) as exc:
        logger.warning("Vibe: Auftrag endete mit %s", getattr(exc, "code", exc))
    except Exception:                                    # noqa: BLE001 – Grenze des Hintergrundauftrags
        logger.exception("Vibe: Auftrag fehlgeschlagen")


@router.get("/state")
def get_state(p: Admin) -> dict:
    """Ohne incus (z. B. Mac ohne Colima) kein Fehler, sondern ein Zustand, den die Seite erklären kann."""
    if not incus.available():
        return {"incus": False, "error_code": "vibe_no_incus", "projects": []}
    return {"incus": True, "error_code": "", "projects": state.projects_of(p.username)}


@router.post("/projects", status_code=status.HTTP_202_ACCEPTED)
async def create_project(p: Admin, body: NewProject) -> dict:
    """Legt an und richtet im Hintergrund ein; die Seite fragt den Fortschritt über /state ab."""
    model = _default_model()
    try:
        out = await projects.create(admin=p.username, name=body.name, model=model)
    except projects.VibeProjectError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None
    task = asyncio.create_task(_background(jobs._setup(out["project_id"])))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"project_id": out["project_id"]}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, p: Admin) -> dict:
    _own(project_id, p)
    await projects.remove(project_id, owner=p.username)
    return {"removed": True}


@router.post("/projects/{project_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry(project_id: str, p: Admin, body: Empty) -> dict:
    _own(project_id, p)
    row = state.get_row(project_id)
    if row["state"] != "failed":
        raise coded(status.HTTP_409_CONFLICT, "vibe_not_failed")
    task = asyncio.create_task(_background(jobs.retry_setup(project_id, owner=p.username)))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"started": True}


@router.post("/projects/{project_id}/chat")
async def open_chat(project_id: str, p: Admin, body: Empty) -> dict:
    """Sitzung für den Chat links (immer dieselbe je Projekt). Weckt einen schlafenden Container."""
    row = _own(project_id, p)
    if row["state"] not in ("ready", "sleeping"):
        raise coded(status.HTTP_409_CONFLICT, "vibe_not_ready")
    try:
        await idle.wake(project_id)
    except container.VibeError as exc:
        raise coded(status.HTTP_503_SERVICE_UNAVAILABLE, exc.code) from None
    from hydrahive.db import sessions as sessions_db
    sid = chat.session_id(row["agent_id"])
    if sid is None:
        sid = sessions_db.create(agent_id=row["agent_id"], user_id=p.username, project_id=project_id,
                                 title=row["name"][:200], metadata={"embedded_in": "vibe"}).id
    else:
        sessions_db.touch(sid)
    return {"session_id": sid, "agent_id": row["agent_id"]}


@router.get("/projects/{project_id}/versions")
async def list_versions(project_id: str, p: Admin) -> dict:
    _own(project_id, p)
    return {"versions": await versions.history(project_id)}


@router.post("/projects/{project_id}/versions/{sha}/restore")
async def restore_version(project_id: str, sha: str, p: Admin, body: Empty) -> dict:
    _own(project_id, p)
    try:
        version_text.check_sha(sha)
        return {"version": await versions.restore(project_id, sha)}
    except version_text.VersionError as exc:
        raise coded(status.HTTP_400_BAD_REQUEST, exc.code) from None


@router.post("/projects/{project_id}/heal")
def heal_switch(project_id: str, p: Admin, body: HealSwitch) -> dict:
    _own(project_id, p)
    state.set_heal(project_id, body.enabled)
    return {"enabled": body.enabled}
