"""Hinweise/Notizen des Schreib-Teams (T1d): lesen (Projektmitglied), abhaken/verwerfen/löschen (Schreibrecht)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from . import team_notes
from ._route_base import Auth, _call, _guard

router = APIRouter()
B = "/projects/{project_id}/books/{book_id}/notes"


class NoteStatusIn(BaseModel):
    status: Literal["open", "done", "dismissed"]


@router.get(B)
def list_notes(project_id: str, book_id: str, auth: Auth, status: Literal["open", "all"] = "open",
               scene_id: str | None = None):
    _guard(auth, project_id, "read")
    return _call(team_notes.list_notes, project_id, book_id, status=status, scene_id=scene_id)


@router.patch(B + "/{note_id}")
def set_status(project_id: str, book_id: str, note_id: str, body: NoteStatusIn, auth: Auth):
    _guard(auth, project_id)
    return _call(team_notes.set_status, project_id, book_id, note_id, body.status)


@router.delete(B + "/{note_id}")
def delete_note(project_id: str, book_id: str, note_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(team_notes.delete, project_id, book_id, note_id)
    return {"deleted": True}
