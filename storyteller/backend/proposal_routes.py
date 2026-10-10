"""Storyteller – Routen für Vorschläge des Agenten (Spec §11.5):
G4b Szenen-Infos (Titel, Zusammenfassung, Perspektive), G4c Steckbriefe (neu/ändern), G4d Gliederung,
C2 Gliederungs-Umbau.

Wird VOR run_routes eingebunden, damit ``…/proposals/info|entities|outline|restructure`` nicht als Szenen-ID von
``…/proposals/{scene_id}`` gelesen werden.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import proposals_entities, proposals_info, proposals_outline, restructure
from ._route_base import Auth, _call, _guard

router = APIRouter()
B = "/projects/{project_id}/books/{book_id}"


class InfoAcceptIn(BaseModel):
    base_version: int
    fields: list[str] | None = Field(default=None, max_length=3)


@router.get(f"{B}/proposals/info")
def info_list(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(proposals_info.list_for_book, project_id, book_id)


@router.post(f"{B}/proposals/{{scene_id}}/info/accept")
def info_accept(project_id: str, book_id: str, scene_id: str, body: InfoAcceptIn, auth: Auth):
    _guard(auth, project_id)
    return _call(proposals_info.accept, project_id, book_id, scene_id, body.base_version, body.fields)


@router.delete(f"{B}/proposals/{{scene_id}}/info")
def info_discard(project_id: str, book_id: str, scene_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(proposals_info.discard, project_id, book_id, scene_id)
    return {"ok": True}


class EntityAcceptIn(BaseModel):
    base_version: int   # Version der Struktur (Steckbriefe liegen in structure.json)


@router.get(f"{B}/proposals/entities")
def entity_list(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(proposals_entities.list_for_book, project_id, book_id)


@router.post(f"{B}/proposals/entities/{{proposal_id}}/accept")
def entity_accept(project_id: str, book_id: str, proposal_id: str, body: EntityAcceptIn, auth: Auth):
    _guard(auth, project_id)
    return _call(proposals_entities.accept, project_id, book_id, proposal_id, body.base_version)


@router.delete(f"{B}/proposals/entities/{{proposal_id}}")
def entity_discard(project_id: str, book_id: str, proposal_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(proposals_entities.discard, project_id, book_id, proposal_id)
    return {"ok": True}


class OutlineAcceptIn(BaseModel):
    outline: dict[str, Any]   # die (ggf. bearbeitete) Fassung; geprüft wie „Gliederung aus Idee“
    base_version: int         # Version der Struktur


@router.get(f"{B}/proposals/outline")
def outline_get(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(proposals_outline.get, project_id, book_id)


@router.post(f"{B}/proposals/outline/accept")
def outline_accept(project_id: str, book_id: str, body: OutlineAcceptIn, auth: Auth):
    _guard(auth, project_id)
    return _call(proposals_outline.accept, project_id, book_id, body.outline, body.base_version)


@router.delete(f"{B}/proposals/outline")
def outline_discard(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(proposals_outline.discard, project_id, book_id)
    return {"ok": True}


@router.get(f"{B}/proposals/restructure")
def restructure_get(project_id: str, book_id: str, auth: Auth):
    """C2: offener Umbau-Vorschlag oder null."""
    _guard(auth, project_id, "read")
    return _call(restructure.find, project_id, book_id)


@router.post(f"{B}/proposals/restructure/accept")
def restructure_accept(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id)
    return _call(restructure.accept, project_id, book_id)


@router.delete(f"{B}/proposals/restructure")
def restructure_discard(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(restructure.discard, project_id, book_id)
    return {"ok": True}
