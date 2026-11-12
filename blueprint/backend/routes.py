"""Blueprint-Routen — /api/modules/blueprint/boards.

Per-User Board-CRUD, ownership-strikt (require_auth). graph_json wird beim
Schreiben als gültiges JSON validiert und auf eine Maximalgröße begrenzt, bevor
es gespeichert wird — kein Schmuggel beliebiger Payloads in die DB.

Ein Board kann einem Projekt zugeordnet sein (access.py prüft den Zugriff).
Die Routen für Vorschlag und frühere Fassungen stehen in routes_proposal.py.
"""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import access, store
from .routes_proposal import router as proposal_router

router = APIRouter()
router.include_router(proposal_router)

Auth = Annotated[tuple[str, str], Depends(require_auth)]

_MAX_GRAPH_BYTES = 2 * 1024 * 1024  # 2 MB — großzügig für komplexe Boards


def _valid_graph(raw: str) -> str:
    if len(raw.encode("utf-8")) > _MAX_GRAPH_BYTES:
        raise coded(status.HTTP_400_BAD_REQUEST, "graph_too_large")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_graph_json")
    if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
        raise coded(status.HTTP_400_BAD_REQUEST, "invalid_graph_shape")
    return raw


def _project(user: str, role: str, project_id: str | None) -> str | None:
    try:
        return access.check_project(user, role, project_id)
    except store.BoardError as exc:
        raise coded(status.HTTP_404_NOT_FOUND, exc.code)


@router.get("/boards")
def list_boards(
    auth: Auth,
    project_id: Annotated[str | None, Query(max_length=64)] = None,
) -> list[dict]:
    """Eigene Boards, auf Wunsch nur die eines Projekts."""
    user, _ = auth
    return store.list_for(user, project_id=project_id or None)


@router.get("/boards/{board_id}")
def get_board(auth: Auth, board_id: int) -> dict:
    user, _ = auth
    board = store.get(user, board_id)
    if board is None:
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return board


class BoardCreate(BaseModel):
    name: str = Field(default="Neues Board", min_length=1, max_length=120)
    project_id: str | None = Field(default=None, max_length=64)


@router.post("/boards", status_code=status.HTTP_201_CREATED)
def create_board(auth: Auth, body: BoardCreate) -> dict:
    user, role = auth
    project = _project(user, role, body.project_id)
    try:
        return store.create(user, body.name.strip() or "Neues Board", project_id=project)
    except store.BoardError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code)


class BoardUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    graph_json: str | None = None
    # Fehlt das Feld, bleibt das Projekt. null löst das Board vom Projekt.
    project_id: str | None = Field(default=None, max_length=64)
    # Stand, den die Zeichenfläche kennt. Weicht er ab, wird nichts gespeichert (409 board_changed).
    base_revision: int | None = Field(default=None, ge=0)
    # Die Fassung, die ersetzt wird, vorher in die früheren Fassungen legen.
    keep_previous: bool = False


@router.put("/boards/{board_id}")
def update_board(auth: Auth, board_id: int, body: BoardUpdate) -> dict:
    user, role = auth
    graph = _valid_graph(body.graph_json) if body.graph_json is not None else None
    name = body.name.strip() if body.name is not None else None
    if name == "":
        name = None
    changes: dict = {"name": name, "graph_json": graph, "base_revision": body.base_revision,
                     "keep_previous": body.keep_previous}
    if "project_id" in body.model_fields_set:
        changes["project_id"] = _project(user, role, body.project_id)
    try:
        updated = store.update(user, board_id, **changes)
    except store.BoardError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code)
    if updated is None:
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return updated


@router.delete("/boards/{board_id}")
def delete_board(auth: Auth, board_id: int) -> dict:
    user, _ = auth
    if not store.remove(user, board_id):
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return {"removed": True}
