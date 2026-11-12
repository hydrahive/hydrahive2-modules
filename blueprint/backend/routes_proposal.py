"""Routen für den Vorschlag des Agenten und frühere Fassungen eines Boards (Etappe 3a).

Ablegen kann einen Vorschlag nur der Agent über das Werkzeug blueprint_propose.
Hier übernimmt oder verwirft der Nutzer ihn und stellt frühere Fassungen wieder her.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded
from pydantic import BaseModel, Field

from . import proposals, store, versions

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


def _not_found():
    return coded(status.HTTP_404_NOT_FOUND, "board_not_found")


class AcceptBody(BaseModel):
    # Zeit des Vorschlags, den der Nutzer vor sich hat. Hat der Agent ihn inzwischen ersetzt: 409 proposal_changed.
    proposal_at: str | None = Field(default=None, max_length=40)


@router.post("/boards/{board_id}/proposal/accept")
def accept_proposal(auth: Auth, board_id: int, body: AcceptBody | None = None) -> dict:
    """Vorschlag übernehmen. Die bisherige Fassung wandert in die Versionen."""
    user, _ = auth
    try:
        board = proposals.accept(user, board_id, body.proposal_at if body else None)
    except store.BoardError as exc:
        raise coded(status.HTTP_409_CONFLICT, exc.code)
    if board is None:
        raise _not_found()
    return board


@router.delete("/boards/{board_id}/proposal")
def discard_proposal(auth: Auth, board_id: int) -> dict:
    """Vorschlag verwerfen. Die Fassung des Nutzers bleibt, wie sie ist."""
    user, _ = auth
    board = proposals.discard(user, board_id)
    if board is None:
        raise _not_found()
    return board


@router.get("/boards/{board_id}/versions")
def list_versions(auth: Auth, board_id: int) -> list[dict]:
    """Frühere Fassungen, neueste zuerst, ohne den Graphen."""
    user, _ = auth
    listed = versions.list_for(user, board_id)
    if listed is None:
        raise _not_found()
    return listed


@router.post("/boards/{board_id}/versions/{version_id}/restore")
def restore_version(auth: Auth, board_id: int, version_id: int) -> dict:
    """Frühere Fassung wiederherstellen. Der aktuelle Stand wird vorher gesichert."""
    user, _ = auth
    if store.get(user, board_id) is None:
        raise _not_found()
    board = versions.restore(user, board_id, version_id)
    if board is None:
        raise coded(status.HTTP_404_NOT_FOUND, "version_not_found")
    return board
