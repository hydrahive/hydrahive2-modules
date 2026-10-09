"""Storyteller — Kapitel-Zusammenfassung (A5c, Spec ki-qualitaet-a5.md §2c): lesen (read), speichern und Vorschlag
erzeugen (write). Erzeugen speichert nichts – die Oberfläche übernimmt den Text erst auf Wunsch."""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import ai, chapter_summaries
from ._files import StoryError
from ._route_base import Auth, _call, _guard

logger = logging.getLogger(__name__)
router = APIRouter()
C = "/projects/{project_id}/books/{book_id}/chapter-summaries"


class ChapterSummaryIn(BaseModel):
    summary: str = Field(max_length=chapter_summaries.MAX_SUMMARY)
    base_version: int


class GenerateIn(BaseModel):
    model: str | None = Field(default=None, max_length=200)


@router.get(C)
def chapter_summaries_get(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return {"chapters": _call(chapter_summaries.get_all, project_id, book_id)}


@router.put(C + "/{chapter_id}")
def chapter_summary_put(project_id: str, book_id: str, chapter_id: str, body: ChapterSummaryIn, auth: Auth):
    _guard(auth, project_id)
    return _call(chapter_summaries.save, project_id, book_id, chapter_id, body.summary, body.base_version)


@router.post(C + "/{chapter_id}/generate")
async def chapter_summary_generate(project_id: str, book_id: str, chapter_id: str, body: GenerateIn, auth: Auth):
    _guard(auth, project_id)
    try:
        key = ai.acquire(auth[0], book_id)
    except ai.AiError as exc:
        return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message}})
    try:
        return await chapter_summaries.generate(project_id, book_id, chapter_id, model=body.model)
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
    except Exception as exc:  # Modell-/Schlüsselfehler lesbar weitergeben
        logger.warning("Kapitel-Zusammenfassung fehlgeschlagen: %s", exc)
        return JSONResponse(status_code=502, content={"detail": {"code": "llm_failed",
                                                                 "message": str(exc)[:300] or exc.__class__.__name__}})
    finally:
        ai.release(key)
