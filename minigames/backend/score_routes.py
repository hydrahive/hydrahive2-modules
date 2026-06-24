"""Score-Routen — /api/modules/minigames/scores[...].

Login-pflichtig, strikt user-scoped fürs Speichern/eigene Abfragen.
Bestenliste ist global (Top-Score je User). Server-Whitelist für game_id +
Plausibilitätsgrenze für score.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth
from hydrahive.api.middleware.errors import coded

from . import scores_store as store
from .games import is_plausible_score, is_valid_game

router = APIRouter()

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class ScoreIn(BaseModel):
    game_id: str = Field(min_length=1, max_length=40)
    score: int = Field(ge=0)


@router.post("/scores")
def submit_score(body: ScoreIn, auth: Auth) -> dict:
    user, _ = auth
    if not is_valid_game(body.game_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_game")
    if not is_plausible_score(body.game_id, body.score):
        raise coded(status.HTTP_400_BAD_REQUEST, "implausible_score")
    is_best = store.add(user, body.game_id, body.score)
    return {"ok": True, "is_personal_best": is_best}


@router.get("/scores/mine")
def my_scores(auth: Auth, game_id: str = Query(min_length=1, max_length=40)) -> dict:
    user, _ = auth
    if not is_valid_game(game_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_game")
    return {"best": store.best_for(user, game_id), "recent": store.recent_for(user, game_id)}


@router.get("/scores/leaderboard")
def get_leaderboard(
    auth: Auth,
    game_id: str = Query(min_length=1, max_length=40),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    if not is_valid_game(game_id):
        raise coded(status.HTTP_400_BAD_REQUEST, "unknown_game")
    return store.leaderboard(game_id, limit)
