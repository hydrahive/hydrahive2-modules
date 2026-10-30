"""Schnittstellen L2 (PLAN-L2.md): GitHub verbinden, Einreichen (Auftrag im Hintergrund), Fehler melden,
Einreichungen. Nur Admins. Der Token taucht in keiner Antwort auf."""
from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import AuthPrincipal, require_admin_principal
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, ConfigDict, Field

from . import github_auth, jobs, report, state, submit
from .submit_box import SubmitError

logger = logging.getLogger(__name__)
router = APIRouter()
Admin = Annotated[AuthPrincipal, Depends(require_admin_principal)]
Target = Literal["core", "modules"]
_waiters: set[asyncio.Task] = set()


class Empty(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: Target
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=4000)


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: Target
    title: str = Field(min_length=1, max_length=120)
    what: str = Field(min_length=1, max_length=4000)
    expected: str = Field(default="", max_length=4000)
    steps: str = Field(default="", max_length=4000)


@router.get("/github")
def github_status(p: Admin) -> dict:
    return {**github_auth.status(), "configured": bool(github_auth.client_id())}


async def _wait() -> None:
    try:
        await github_auth.wait()
    except github_auth.GitHubError as e:
        logger.info("Hydra-Labor: GitHub-Verbindung nicht zustande gekommen (%s)", e.code)


@router.post("/github/connect")
async def github_connect(p: Admin, body: Empty) -> dict:
    try:
        out = await github_auth.start()
    except github_auth.GitHubError as e:
        raise coded(status.HTTP_409_CONFLICT, e.code) from None
    task = asyncio.get_running_loop().create_task(_wait())       # wartet bis zur Freigabe auf GitHub
    _waiters.add(task)
    task.add_done_callback(_waiters.discard)
    return out


@router.post("/github/disconnect")
def github_disconnect(p: Admin, body: Empty) -> dict:
    github_auth.disconnect()
    return github_auth.status()


@router.get("/submit/target")
async def submit_target(p: Admin) -> dict:
    if state.get()["step"] != "ready":
        raise coded(status.HTTP_409_CONFLICT, "labor_not_ready")
    return {"target": await submit.suggest_target()}


@router.post("/submit", status_code=status.HTTP_202_ACCEPTED)
async def submit_start(p: Admin, body: SubmitIn) -> dict:
    if state.get()["step"] != "ready":
        raise coded(status.HTTP_409_CONFLICT, "labor_not_ready")
    if state.get()["running"]:
        raise coded(status.HTTP_409_CONFLICT, "labor_busy")
    state.set_submit_in(body.model_dump())
    if not jobs.start("submit"):
        raise coded(status.HTTP_409_CONFLICT, "labor_busy")
    return {"started": "submit"}


@router.post("/report")
async def report_issue(p: Admin, body: ReportIn) -> dict:
    try:
        return await report.report(body.target, body.title, body.what, body.expected, body.steps)
    except SubmitError as e:
        raise coded(status.HTTP_409_CONFLICT, e.code) from None
    except github_auth.GitHubError as e:
        raise coded(status.HTTP_502_BAD_GATEWAY, e.code) from None


@router.get("/submissions")
def submissions(p: Admin) -> dict:
    return {"items": submit.list_submissions()}


@router.post("/submissions/refresh")
async def submissions_refresh(p: Admin, body: Empty) -> dict:
    try:
        await submit.refresh()
    except SubmitError as e:
        raise coded(status.HTTP_409_CONFLICT, e.code) from None
    return {"items": submit.list_submissions()}
