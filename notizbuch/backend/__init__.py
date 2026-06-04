"""Notizbuch-Modul Backend — Notizen pro User (CRUD), ownership-strikt.

register(ctx) -> Router (/api/modules/notizbuch/...) + Migrationen. Jede Notiz
gehört dem anlegenden User (require_auth); fremde Notizen sind unsichtbar/404.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from hydrahive.db.connection import db

router = APIRouter()

# Festes SQL-Literal (KEIN User-Input) — daher sicher per f-string interpolierbar.
# Ein Bind-Param würde den String speichern statt strftime auszuwerten. Nicht durch
# eingehende Werte ersetzen.
_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


class NoteIn(BaseModel):
    title: str = Field(default="", max_length=500)
    body: str = Field(default="", max_length=1_000_000)


@router.get("/notes")
def list_notes(auth: Annotated[tuple[str, str], Depends(require_auth)]) -> list[dict]:
    user, _ = auth
    with db() as c:
        return [
            dict(r) for r in c.execute(
                'SELECT id, title, updated_at FROM module_notizbuch_notes '
                'WHERE "user" = ? ORDER BY updated_at DESC',
                (user,),
            ).fetchall()
        ]


@router.get("/notes/{note_id}")
def get_note(note_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        row = c.execute(
            'SELECT id, title, body, created_at, updated_at FROM module_notizbuch_notes '
            'WHERE id = ? AND "user" = ?',
            (note_id, user),
        ).fetchone()
    if row is None:
        raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
    return dict(row)


@router.post("/notes")
def create_note(body: NoteIn, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        cur = c.execute(
            'INSERT INTO module_notizbuch_notes ("user", title, body) VALUES (?, ?, ?)',
            (user, body.title, body.body),
        )
        row = c.execute(
            'SELECT id, title, body, created_at, updated_at FROM module_notizbuch_notes WHERE id = ?',
            (cur.lastrowid,),
        ).fetchone()
    return dict(row)


@router.put("/notes/{note_id}")
def update_note(
    note_id: int,
    body: NoteIn,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    user, _ = auth
    with db() as c:
        cur = c.execute(
            f'UPDATE module_notizbuch_notes SET title = ?, body = ?, updated_at = {_NOW} '
            'WHERE id = ? AND "user" = ?',
            (body.title, body.body, note_id, user),
        )
        if cur.rowcount == 0:
            raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
        row = c.execute(
            'SELECT id, title, body, created_at, updated_at FROM module_notizbuch_notes WHERE id = ?',
            (note_id,),
        ).fetchone()
    return dict(row)


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, auth: Annotated[tuple[str, str], Depends(require_auth)]) -> dict:
    user, _ = auth
    with db() as c:
        cur = c.execute(
            'DELETE FROM module_notizbuch_notes WHERE id = ? AND "user" = ?',
            (note_id, user),
        )
        if cur.rowcount == 0:
            raise coded(status.HTTP_404_NOT_FOUND, "note_not_found")
    return {"ok": True}


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_migrations("migrations")
