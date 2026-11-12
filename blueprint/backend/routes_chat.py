"""Routen für den Chat neben dem Board (Etappe 3b)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import chat, store

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _board(user: str, board_id: int) -> dict:
    board = store.get(user, board_id)
    if board is None:
        raise coded(status.HTTP_404_NOT_FOUND, "board_not_found")
    return board


@router.get("/boards/{board_id}/chat")
def chat_info(auth: Auth, board_id: int) -> dict:
    """Agent neben dem Board, ob der Nutzer starten darf, fehlende Werkzeuge."""
    user, role = auth
    return chat.describe(user, role, _board(user, board_id))


@router.post("/boards/{board_id}/chat")
def chat_start(auth: Auth, board_id: int) -> dict:
    """Sitzung zu diesem Board holen oder anlegen. Liefert die Sitzung und den Einstiegstext."""
    user, role = auth
    board = _board(user, board_id)
    try:
        return chat.start(user, role, board)
    except store.BoardError as exc:
        forbidden = exc.code == "project_read_only"
        raise coded(status.HTTP_403_FORBIDDEN if forbidden else status.HTTP_409_CONFLICT, exc.code)
