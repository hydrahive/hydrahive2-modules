"""A3 – Routen für den Papierkorb (Spec nichts-geht-verloren.md §3). Lesen: read. Wiederherstellen: write."""
from __future__ import annotations

from fastapi import APIRouter

from . import trash, trash_books
from ._route_base import Auth, _call, _guard

router = APIRouter()
BK = "/projects/{project_id}/books/{book_id}/trash/scenes"
PJ = "/projects/{project_id}/trash/books"


@router.get(BK)
def scenes(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(trash.list_scenes, project_id, book_id)


@router.post(BK + "/{entry_id}/restore")
def restore_scene(project_id: str, book_id: str, entry_id: str, auth: Auth):
    _guard(auth, project_id)
    return _call(trash.restore_scene, project_id, book_id, entry_id)


@router.get(PJ)
def books(project_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(trash_books.list_books, project_id)


@router.post(PJ + "/{entry_id}/restore")
def restore_book(project_id: str, entry_id: str, auth: Auth):
    _guard(auth, project_id)
    return _call(trash_books.restore_book, project_id, entry_id)
