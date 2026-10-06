"""Storyteller — Routen für Bücher (Liste, Anlegen, Import, Öffnen, Ändern, Papierkorb, Struktur)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import importer, storage
from ._route_base import Auth, _call, _guard, _set
from .routes_scenes import router as scenes_router

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



class StructureIn(BaseModel):
    base_version: int
    structure: dict[str, Any]


@router.get("/projects/{project_id}/books")
def list_books(project_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(storage.list_books, project_id)


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

    def _all():
        st = storage.get_structure(project_id, book_id)
        ids = [s for p in st["parts"] for c in p["chapters"] for s in c["scenes"]]
        return {"book": storage.get_book(project_id, book_id), "structure": st,
                "scenes": {s: storage.get_scene(project_id, book_id, s) for s in ids}}
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
