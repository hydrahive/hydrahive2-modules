"""Storyteller G4b – Routen für Vorschläge zu Szenen-Infos (Titel, Zusammenfassung, Perspektive), Spec §11.5.

Wird VOR run_routes eingebunden, damit ``…/proposals/info`` nicht als Szenen-ID von ``…/proposals/{scene_id}``
gelesen wird.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from . import proposals_info
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
