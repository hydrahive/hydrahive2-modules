"""Ergebnis-Routen — /api/modules/boardgames/results[...].

Login-pflichtig, user-scoped fürs Speichern/eigene Bilanz. Bestenliste global
(meiste Siege). Whitelist für game_id/mode/result.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import results_store as store
from .games import is_valid_game, is_valid_mode, is_valid_result

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class ResultIn(BaseModel):
    game_id: str = Field(min_length=1, max_length=40)
    mode: str = Field(min_length=1, max_length=20)
    result: str = Field(min_length=1, max_length=10)
    opponent: str = Field(default="", max_length=80)


@router.post("/results")
def submit_result(body: ResultIn, auth: Auth) -> dict:
    user, _ = auth
    if not is_valid_game(body.game_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_game")
    if not is_valid_mode(body.mode):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_mode")
    if not is_valid_result(body.result):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_result")
    store.add(user, body.game_id, body.mode, body.result, body.opponent.strip())
    return {"ok": True}


@router.get("/results/mine")
def my_record(
    auth: Auth,
    game_id: str = Query(min_length=1, max_length=40),
    mode: str | None = Query(default=None, max_length=20),
) -> dict:
    user, _ = auth
    if not is_valid_game(game_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_game")
    if mode is not None and not is_valid_mode(mode):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_mode")
    return store.record_for(user, game_id, mode)


@router.get("/results/leaderboard")
def get_leaderboard(
    auth: Auth,
    game_id: str = Query(min_length=1, max_length=40),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    if not is_valid_game(game_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_game")
    return store.leaderboard(game_id, limit)
