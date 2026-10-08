"""Storyteller — Routen Ghostwriter G2 (Spec ghostwriter.md §9): Lauf (Schätzung, Start, Stand, Abbrechen),
Gliederung aus Idee, abgelegte Vorschläge. Lesen: Rolle read. Alles, was schreibt oder KI kostet: write."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hydrahive.api.middleware.errors import coded

from . import ai, outline, proposals, run_engine, run_plan, runs, storage
from ._files import StoryError
from ._route_base import Auth, _call, _guard

logger = logging.getLogger(__name__)
router = APIRouter()
B = "/projects/{project_id}/books/{book_id}"


class RunIn(BaseModel):
    scope: str = Field(max_length=10)
    chapter_id: str | None = Field(default=None, max_length=64)
    scene_id: str | None = Field(default=None, max_length=64)
    skip_filled: bool = True
    length_words: int | None = Field(default=None, ge=200, le=6000)
    source: str = Field(default="outline", max_length=12)   # outline | interview (G3)
    confirm: bool = False
    confirm_over_limit: bool = False


class OutlineIn(BaseModel):
    idea: str = Field(default="", max_length=4000)
    hints: str = Field(default="", max_length=2000)
    chapters: int = Field(ge=1, le=outline.MAX_CHAPTERS)
    scenes_per_chapter: int = Field(ge=1, le=outline.MAX_SCENES_PER_CHAPTER)


class OutlineApplyIn(BaseModel):
    outline: dict[str, Any]
    base_version: int


class AcceptIn(BaseModel):
    base_version: int


def _err(status: int, code: str, message: str = "") -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message": message}})


@router.get(f"{B}/ghost/run/estimate")
def run_estimate(project_id: str, book_id: str, scope: str, auth: Auth, chapter_id: str | None = None,
                 scene_id: str | None = None, skip_filled: bool = True, length_words: int | None = None,
                 source: str = "outline"):
    _guard(auth, project_id, "read")
    out = _call(run_plan.plan, project_id, book_id, scope=scope, chapter_id=chapter_id, scene_id=scene_id,
                skip_filled=skip_filled, length_words=length_words, source=source)
    if isinstance(out, dict):
        out.pop("scene_ids", None)
    return out


@router.post(f"{B}/ghost/run")
async def run_start(project_id: str, book_id: str, body: RunIn, auth: Auth):
    """async: der Lauf wird in der Ereignisschleife des Servers gestartet (asyncio.create_task)."""
    _guard(auth, project_id)
    if runs.active_run(project_id, book_id):
        return _err(409, "run_active", "Für dieses Buch läuft schon ein Ghostwriter-Lauf.")
    try:
        # Planung liest viele Dateien → im Thread, damit der Server nicht blockiert.
        p = await asyncio.to_thread(run_plan.plan, project_id, book_id, scope=body.scope, chapter_id=body.chapter_id,
                                    scene_id=body.scene_id, skip_filled=body.skip_filled, length_words=body.length_words,
                                    source=body.source)
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
    if not p["scene_ids"]:
        return _err(400, "nothing_to_write")
    if not body.confirm:
        return _err(400, "confirm_required")
    # Grenze je Auftrag: Eingabe + Ausgabe (Spec kostengrenze.md §4). Bestätigt → gilt für diesen Lauf nicht.
    if p["limit_tokens"] and p["total_tokens"] > p["limit_tokens"] and not body.confirm_over_limit:
        return _err(400, "over_limit")
    try:
        key = ai.acquire(auth[0], book_id)
    except ai.AiError as exc:
        return _err(exc.status, exc.code, exc.message)
    options = {"skip_filled": body.skip_filled, "length_words": body.length_words or 0,
               "limit_tokens": 0 if body.confirm_over_limit else p["limit_tokens"], "source": body.source,
               "chapter_id": body.chapter_id or ""}
    run = runs.create_run(user=auth[0], project_id=project_id, book_id=book_id, scope=body.scope,
                          scene_ids=p["scene_ids"], model=p["model"], options=options)
    run_engine.start_background(run["id"], project_id, book_id, auth[0], key)
    return runs.get_run(project_id, book_id, run["id"])


@router.get(f"{B}/ghost/run")
def run_get(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    _call(storage.get_book, project_id, book_id)
    return runs.latest_run(project_id, book_id)


@router.post(f"{B}/ghost/run/cancel")
async def run_cancel(project_id: str, book_id: str, auth: Auth):
    _guard(auth, project_id)
    run = runs.active_run(project_id, book_id)
    if not run:
        return {"ok": True}
    run_engine.cancel(run["id"])
    if run["id"] not in run_engine.live_ids():
        # Kein lebender Task (noch nicht gestartet oder verloren) → direkt beenden, Sperre frei.
        runs.update_run(run["id"], status="cancelled")
        ai.release((run["username"], book_id))
    return {"ok": True}


@router.post(f"{B}/ghost/outline")
async def outline_generate(project_id: str, book_id: str, body: OutlineIn, auth: Auth):
    _guard(auth, project_id)
    try:
        key = ai.acquire(auth[0], book_id)
    except ai.AiError as exc:
        return _err(exc.status, exc.code, exc.message)
    try:
        return await outline.generate(project_id, book_id, idea=body.idea, chapters=body.chapters,
                                      scenes_per_chapter=body.scenes_per_chapter, hints=body.hints)
    except StoryError as exc:
        raise coded(exc.status, exc.code) from exc
    except Exception as exc:  # Modell-/Schlüsselfehler lesbar weitergeben
        logger.warning("Gliederung fehlgeschlagen: %s", exc)
        return _err(502, "llm_failed", str(exc)[:300] or exc.__class__.__name__)
    finally:
        ai.release(key)


@router.post(f"{B}/ghost/outline/apply")
def outline_apply(project_id: str, book_id: str, body: OutlineApplyIn, auth: Auth):
    _guard(auth, project_id)
    return _call(outline.apply, project_id, book_id, body.outline, body.base_version)


@router.get(f"{B}/proposals/{{scene_id}}")
def proposal_get(project_id: str, book_id: str, scene_id: str, auth: Auth):
    _guard(auth, project_id, "read")
    return _call(proposals.get, project_id, book_id, scene_id)


@router.post(f"{B}/proposals/{{scene_id}}/accept")
def proposal_accept(project_id: str, book_id: str, scene_id: str, body: AcceptIn, auth: Auth):
    _guard(auth, project_id)
    return _call(proposals.accept, project_id, book_id, scene_id, body.base_version)


@router.delete(f"{B}/proposals/{{scene_id}}")
def proposal_discard(project_id: str, book_id: str, scene_id: str, auth: Auth):
    _guard(auth, project_id)
    _call(proposals.discard, project_id, book_id, scene_id)
    return {"ok": True}
