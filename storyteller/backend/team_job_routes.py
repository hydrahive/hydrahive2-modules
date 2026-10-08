"""Team-Knöpfe (T1e): Katalog, Schätzung, Start, Liste, Abbruch.

Rechte wie beim Chat mit dem Team: Lesen (Katalog, Liste) jedes Projektmitglied; Schätzen, Starten, Abbrechen nur mit
Schreibrecht (kostet Geld). Beauftragt wird nur ein Helfer DIESES Projekts (``team.helper_for``) – keine freie
Agent-ID von außen. Kosten werden mit dem Modell des Helfers geschätzt (mit dem läuft er).
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import storage, team, team_job_estimate, team_job_run, team_jobs
from ._files import StoryError
from ._route_base import Auth, _call, _guard
from .team import jobs_catalog

router = APIRouter()
B = "/projects/{project_id}/books/{book_id}/team/jobs"


class JobIn(BaseModel):
    job: str = Field(max_length=40)
    place_id: str = Field(max_length=64)


def _project(project_id: str) -> dict:
    from hydrahive.projects import config as project_config
    return project_config.get(project_id) or {}


def _helper(project_id: str, job: jobs_catalog.Job) -> dict:
    agent = team.helper_for(_project(project_id), job.role)
    if agent is None:
        raise StoryError("helper_missing", 409)
    return agent


def _estimate(project_id: str, book_id: str, body: JobIn) -> tuple[jobs_catalog.Job, dict, dict]:
    storage.get_book(project_id, book_id)
    job = jobs_catalog.get(body.job)
    agent = _helper(project_id, job)
    est = team_job_estimate.estimate(project_id, book_id, job, body.place_id, model=agent.get("llm_model") or "")
    return job, agent, est


@router.get(B + "/catalog")
def catalog(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    _call(storage.get_book, project_id, book_id)
    project = _project(project_id)
    return [{"key": j.key, "label": j.label, "scope": j.scope, "role": j.role,
             "available": team.helper_for(project, j.role) is not None} for j in jobs_catalog.JOBS]


@router.get(B)
def list_jobs(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(team_jobs.list_jobs, project_id, book_id)


@router.post(B + "/estimate")
def estimate(project_id: str, book_id: str, body: JobIn, auth: Auth):
    _guard(auth, project_id)
    return _call(lambda: _estimate(project_id, book_id, body)[2])


def _start(project_id: str, book_id: str, body: JobIn, user: str) -> dict:
    job, agent, est = _estimate(project_id, book_id, body)
    book = storage.get_book(project_id, book_id)
    row = team_jobs.create(project_id, book_id, {
        "job": job.key, "role": job.role, "agent_id": agent["id"], "agent_name": agent.get("name") or "",
        "place_id": body.place_id, "place_title": est["place_title"], "estimate_micros": est["cost_micros"],
        "user": user})
    task = jobs_catalog.task_text(job, book_id=book_id, book_title=book["title"], place_id=body.place_id,
                                  place_title=est["place_title"])
    team_job_run.start(project_id, book_id, row["id"], task=task)
    return row


@router.post(B)
async def start(project_id: str, book_id: str, body: JobIn, auth: Auth):
    """async: der Lauf wird in der Ereignisschleife des Servers gestartet (asyncio.create_task)."""
    _guard(auth, project_id)
    return _call(_start, project_id, book_id, body, auth[0])


@router.post(B + "/{job_id}/cancel")
async def cancel(project_id: str, book_id: str, job_id: str, auth: Auth):
    """async: findet und stoppt den Lauf-Task in der Ereignisschleife des Servers."""
    _guard(auth, project_id)
    _call(team_job_run.cancel, project_id, book_id, job_id)
    return _call(team_jobs.get, project_id, book_id, job_id)
