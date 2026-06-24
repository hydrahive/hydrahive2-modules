"""Schach-spezifische Routen — /api/modules/boardgames/chess/[...].

Aktuell nur der LLM-Gegner: nimmt FEN + die Liste legaler Züge (UCI) vom
Frontend und lässt das gewählte Modell daraus wählen. Login-pflichtig.
Die Engine bleibt im Frontend maßgeblich — hier passiert keine Spiel-Logik,
nur die LLM-Auswahl aus bereits validierten Zügen.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from hydrahive.api.middleware.auth import require_auth

from .chess_llm import choose_move

router = APIRouter(prefix="/chess")

Auth = Annotated[tuple[str, str], Depends(require_auth)]


class LlmMoveIn(BaseModel):
    model: str | None = Field(default=None, max_length=120)
    fen: str = Field(min_length=1, max_length=120)
    moves: list[str] = Field(min_length=1, max_length=256)
    history: list[str] = Field(default_factory=list, max_length=512)


@router.post("/llm-move")
async def llm_move(body: LlmMoveIn, auth: Auth) -> dict:
    """Lässt das gewählte Modell einen Zug aus `moves` wählen.

    Antwort: {"move": <uci>|null, "index": <int>, "source": "llm"|"invalid"}.
    Bei einem unbrauchbaren Modell-Zug ist `move` null — das Frontend nutzt dann
    seinen Minimax-Fallback. Wir geben hier nie einen Fehler-Status zurück, damit
    eine Partie an LLM-Aussetzern nicht abbricht.
    """
    moves = [m.strip().lower() for m in body.moves if m.strip()]
    history = [m.strip().lower() for m in body.history if m.strip()]
    return await choose_move(
        model=body.model, fen=body.fen, moves=moves, history=history,
    )
