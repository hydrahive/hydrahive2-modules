"""Blueprint-Routen — /api/modules/blueprint/boards.

Per-User Board-CRUD, ownership-strikt (require_auth). graph_json wird beim
Schreiben als gültiges JSON validiert und auf eine Maximalgröße begrenzt, bevor
es gespeichert wird — kein Schmuggel beliebiger Payloads in die DB.
"""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import store

router = APIRouter()

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


@router.get("/boards")
def list_boards(auth: Auth) -> list[dict]:
    user, _ = auth
    return store.list_for(user)


@router.get("/boards/{board_id}")
def get_board(auth: Auth, board_id: int) -> dict:
    user, _ = auth
    board = store.get(user, board_id)
    if board is None:
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return board


class BoardCreate(BaseModel):
    name: str = Field(default="Neues Board", min_length=1, max_length=120)


@router.post("/boards", status_code=status.HTTP_201_CREATED)
def create_board(auth: Auth, body: BoardCreate) -> dict:
    user, _ = auth
    try:
        return store.create(user, body.name.strip() or "Neues Board")
    except ValueError:
        raise coded(status.HTTP_409_CONFLICT, "boards_full")


class BoardUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    graph_json: str | None = None


@router.put("/boards/{board_id}")
def update_board(auth: Auth, board_id: int, body: BoardUpdate) -> dict:
    user, _ = auth
    graph = _valid_graph(body.graph_json) if body.graph_json is not None else None
    name = body.name.strip() if body.name is not None else None
    if name == "":
        name = None
    updated = store.update(user, board_id, name=name, graph_json=graph)
    if updated is None:
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return updated


@router.delete("/boards/{board_id}")
def delete_board(auth: Auth, board_id: int) -> dict:
    user, _ = auth
    if not store.remove(user, board_id):
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return {"removed": True}
