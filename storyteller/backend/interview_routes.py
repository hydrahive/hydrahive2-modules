"""Storyteller — Routen Ghostwriter G3 (Spec ghostwriter.md §10): Interview je Kapitel lesen/speichern,
Fragen vorschlagen lassen. Lesen: Rolle read. Speichern und KI: write. Geschrieben wird über den Lauf (run_routes,
source=interview)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import ai, interview_ai, interviews
from ._files import StoryError
from ._route_base import Auth, _call, _guard

logger = logging.getLogger(__name__)
router = APIRouter()
I = "/projects/{project_id}/books/{book_id}/interviews/{chapter_id}"


class InterviewIn(BaseModel):
    base_version: int
    questions: list[Any]


class QuestionsIn(BaseModel):
    count: int = Field(ge=1, le=8)


@router.get(I)
def interview_get(project_id: str, book_id: str, chapter_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(interviews.get, project_id, book_id, chapter_id)


@router.put(I)
def interview_put(project_id: str, book_id: str, chapter_id: str, body: InterviewIn, auth: Auth):
    _guard(auth, project_id)
    return _call(interviews.save, project_id, book_id, chapter_id, body.questions, body.base_version)


@router.post(f"{I}/questions")
async def interview_questions(project_id: str, book_id: str, chapter_id: str, body: QuestionsIn, auth: Auth):
    """Neue Fragen vorschlagen. Gespeichert wird nichts – die Oberfläche übernimmt sie ins Interview."""
    _guard(auth, project_id)
    try:
        key = ai.acquire(auth[0], book_id)
    except ai.AiError as exc:
        return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message}})
    try:
        return {"questions": await interview_ai.suggest_questions(project_id, book_id, chapter_id, count=body.count)}
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
    except Exception as exc:  # Modell-/Schlüsselfehler lesbar weitergeben
        logger.warning("Interview-Fragen fehlgeschlagen: %s", exc)
        return JSONResponse(status_code=502, content={"detail": {"code": "llm_failed",
                                                                 "message": str(exc)[:300] or exc.__class__.__name__}})
    finally:
        ai.release(key)
