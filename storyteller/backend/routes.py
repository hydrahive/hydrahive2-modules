"""Storyteller — Routen für Bücher (Liste, Anlegen, Import, Öffnen, Ändern, Papierkorb, Struktur)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import (
    importer,
    proposals,
    proposals_entities,
    proposals_info,
    proposals_outline,
    storage,
    team_notes,
)
from ._files import project_access
from ._route_base import Auth, _call, _guard, _set
from .chat_routes import router as chat_router
from .ghost_routes import router as ghost_router
from .interview_routes import router as interview_router
from .note_routes import router as note_router
from .proposal_history_routes import router as proposal_history_router
from .proposal_routes import router as proposal_router
from .routes_scenes import router as scenes_router
from .run_routes import router as run_router
from .team import move as team_move
from .team import upgrade as team_upgrade
from .team_job_routes import router as team_job_router
from .team_routes import router as team_router

router = APIRouter()


@router.get("/status")
def status_(_: Auth) -> dict:
    return {"stage": "files", "storage": "project", "ai": "llm"}


class BookIn(BaseModel):
    title: str = Field(max_length=200)
    kind: str = Field(max_length=20)
    language: str = Field(default="de", max_length=5)
    audience: str = Field(default="", max_length=200)
    idea: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=50_000)
    model: str = Field(default="", max_length=200)


class BookPatch(BaseModel):
    base_version: int
    title: str | None = Field(default=None, max_length=200)
    audience: str | None = Field(default=None, max_length=200)
    idea: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=50_000)
    model: str | None = Field(default=None, max_length=200)
    ghost: dict[str, Any] | None = None  # Prüfung in _ghost_settings.merge_ghost



class StructureIn(BaseModel):
    base_version: int
    structure: dict[str, Any]


@router.get("/projects/{project_id}/books")
def list_books(project_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    is_book_project = team_move.is_book_project(project_id)   # T1f: „In eigenes Projekt umziehen“ nur in normalen
    return [{**b, "is_book_project": is_book_project} for b in _call(storage.list_books, project_id)]


@router.post("/projects/{project_id}/books")
def create_book(project_id: str, body: BookIn, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.create_book, project_id, body.model_dump())


@router.post("/projects/{project_id}/books/import")
def import_book(project_id: str, body: dict[str, Any], auth: Auth):
    """Ganzes Buch auf einmal (Beispielbuch, Übernahme aus dem Entwurf). Prüft alles vor dem Schreiben."""
    _guard(auth, project_id)
    return _call(importer.import_book, project_id, body)


@router.get("/projects/{project_id}/books/{book_id}")
def open_book(project_id: str, book_id: str, auth: Auth):
    """Alles zum Öffnen: Kopf, Struktur und alle Szenen (Text + Infos)."""
    _guard(auth, project_id, "read")
    team_upgrade.ensure_current(project_id)   # T1d: Schreib-Team älterer Versionen nachziehen (nur Buch-Projekte)

    def _all():
        st = storage.get_structure(project_id, book_id)
        ids = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
        return {"book": storage.get_book(project_id, book_id), "structure": st,
                "scenes": {s: storage.get_scene(project_id, book_id, s) for s in ids},
                # Oberfläche sperrt Knöpfe für Leser (der Server prüft trotzdem jeden Aufruf).
                "can_write": project_access(auth[0], auth[1], project_id, "write") == "ok",
                "proposals": proposals.list_for_book(project_id, book_id),
                "info_proposals": proposals_info.list_for_book(project_id, book_id),
                "entity_proposals": proposals_entities.list_for_book(project_id, book_id),
                "outline_proposal": proposals_outline.find(project_id, book_id),
                "open_notes": team_notes.open_counts(project_id, book_id)}
    return _call(_all)


@router.patch("/projects/{project_id}/books/{book_id}")
def patch_book(project_id: str, book_id: str, body: BookPatch, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.update_book, project_id, book_id, _set(body), body.base_version)


@router.delete("/projects/{project_id}/books/{book_id}")
def delete_book(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(storage.delete_book, project_id, book_id)
    return {"ok": True}


@router.put("/projects/{project_id}/books/{book_id}/structure")
def put_structure(project_id: str, book_id: str, body: StructureIn, auth: Auth):
    _guard(auth, project_id)
    return _call(storage.save_structure, project_id, book_id, body.structure, body.base_version)


router.include_router(scenes_router)
router.include_router(ghost_router)
router.include_router(proposal_router)   # vor run_router: …/proposals/info, …/proposals/entities
router.include_router(run_router)
router.include_router(interview_router)
router.include_router(chat_router)
router.include_router(team_router)
router.include_router(note_router)
router.include_router(proposal_history_router)
router.include_router(team_job_router)
