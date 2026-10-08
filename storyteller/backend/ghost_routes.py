"""Storyteller — Ghostwriter-Routen (Spec ghostwriter.md §5): Szene schreiben (Server-Sent Events),
Schätzung vorab, Gedächtnis-Zusammenfassung nach dem Annehmen."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import _cost, ai, ghost, storage
from ._files import StoryError
from ._ghost_settings import ghost_of
from ._route_base import Auth, _guard

logger = logging.getLogger(__name__)
router = APIRouter()


class GhostSceneIn(BaseModel):
    scene_id: str = Field(max_length=64)
    length_words: int | None = Field(default=None, ge=200, le=6000)
    model: str | None = Field(default=None, max_length=200)
    confirm_over_limit: bool = False   # Schätzung über der Kostengrenze bewusst bestätigt (Spec kostengrenze.md §4)


class SceneRef(BaseModel):
    scene_id: str = Field(max_length=64)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _over_limit(book: dict, est: dict) -> bool:
    """Grenze je Auftrag: Eingabe + Ausgabe; 0 = aus."""
    limit = ghost_of(book)["limit_tokens"]
    return bool(limit) and est["input_tokens"] + est["output_tokens"] > limit


def _prepare(project_id: str, book_id: str, scene_id: str):
    return storage.get_book(project_id, book_id), ghost.build_material(project_id, book_id, scene_id)


def _ai_error(exc: ai.AiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"detail": {"code": exc.code, "message": exc.message}})


@router.post("/projects/{project_id}/books/{book_id}/ghost/scene")
async def ghost_scene(project_id: str, book_id: str, body: GhostSceneIn, auth: Auth):
    _guard(auth, project_id)
    try:
        book, material = await asyncio.to_thread(_prepare, project_id, book_id, body.scene_id)   # A4: Dateien im Thread
        length, chunk = ghost.plan_lengths(book, body.length_words)
        model = ghost.choose_model(book, body.model)
        est = _cost.scene_estimate(material, length_words=length, chunk_words=chunk)
        if _over_limit(book, est) and not body.confirm_over_limit:
            return JSONResponse(status_code=400, content={"detail": {"code": "over_limit", "message": ""}})
        key = ai.acquire(auth[0], book_id)
    except ai.AiError as exc:
        return _ai_error(exc)
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc

    async def events():
        text = ""   # Wörter am Ende aus dem Ganzen zählen – Stücke trennen Wörter mitten drin
        try:
            gen = ghost.write_scene(material, model=model, length_words=length, chunk_words=chunk)
            try:
                async for piece in gen:
                    text += piece
                    yield _sse("delta", {"text": piece})
            finally:
                await gen.aclose()
            yield _sse("done", {"words": len(text.split()), "model": model or "", "mode": material.mode})
        except Exception as exc:  # Modell-/Schlüssel-/Netzfehler lesbar an die Oberfläche geben
            logger.warning("Ghostwriter-Lauf fehlgeschlagen: %s", exc)
            yield _sse("error", {"code": "llm_failed", "message": str(exc)[:300] or exc.__class__.__name__})
        finally:
            ai.release(key)  # auch wenn der Browser abbricht (Generator wird geschlossen)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/projects/{project_id}/books/{book_id}/ghost/estimate")
def ghost_estimate(project_id: str, book_id: str, scene_id: str, auth: Auth, length_words: int | None = None):
    """Grobe Schätzung (Zeichen/4 bzw. Wörter × 1,6) – nur zur Orientierung vor dem Start."""
    _guard(auth, project_id, "read")
    try:
        book = storage.get_book(project_id, book_id)
        material = ghost.build_material(project_id, book_id, scene_id)
        length, chunk = ghost.plan_lengths(book, length_words)
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
    e = _cost.scene_estimate(material, length_words=length, chunk_words=chunk)
    return {"model": ghost.choose_model(book, None) or "", "length_words": length, **e,
            "total_tokens": e["input_tokens"] + e["output_tokens"], "limit_tokens": ghost_of(book)["limit_tokens"]}


@router.post("/projects/{project_id}/books/{book_id}/ghost/summarize")
async def ghost_summarize(project_id: str, book_id: str, body: SceneRef, auth: Auth):
    """Gedächtnis: Zusammenfassung erzeugen, aber nur wenn das Feld leer ist (Autorentext hat Vorrang)."""
    _guard(auth, project_id)
    try:
        key = ai.acquire(auth[0], book_id)
    except ai.AiError as exc:
        return _ai_error(exc)
    try:
        return await ghost.summarize_scene(project_id, book_id, body.scene_id)
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": {"code": "llm_failed", "message": str(exc)[:300]}})
    finally:
        ai.release(key)
