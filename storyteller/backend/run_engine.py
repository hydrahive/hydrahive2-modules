"""Ghostwriter G2 – Lauf im Hintergrund (Spec ghostwriter.md §9.2–§9.4).

Je Szene: Material (mit dem aktuellen Gedächtnis) → schreiben in Abschnitten (ghost.write_scene) →
ablegen. Ablegen nie still überschreibend: leer UND unverändert seit dem Start → direkt in die Szene
(ai_draft); sonst abgelegter Vorschlag (proposals.py). Abbrechen beendet den laufenden Modellaufruf.
Vor jeder Szene wird die Kostengrenze geprüft. Die KI-Sperre des Buchs wird in jedem Fall freigegeben.
"""
from __future__ import annotations

import asyncio
import logging

from . import _cost, ai, ghost, proposals, runs, storage
from ._files import StoryError
from ._ghost_settings import ghost_of
from .interview_ai import interview_material
from .storage import Conflict

logger = logging.getLogger(__name__)
_cancelled: set[str] = set()


def cancel(run_id: str) -> None:
    _cancelled.add(run_id)


def live_ids() -> set[str]:
    """IDs der Läufe, die in diesem Prozess gerade einen lebenden Task haben."""
    return runs._live_run_ids()


class _Stop(Exception):
    """Abbruch durch den Nutzer (innerhalb des Laufs)."""


class _Limit(Exception):
    """Nächste Szene würde die Kostengrenze überschreiten."""


async def _write(run_id: str, material, *, model, length: int, chunk: int) -> str:
    gen = ghost.write_scene(material, model=model, length_words=length, chunk_words=chunk)
    text = ""
    try:
        async for piece in gen:
            if run_id in _cancelled:
                raise _Stop
            text += piece
    finally:
        await gen.aclose()   # schließt auch die Verbindung zum Modell
    if run_id in _cancelled:
        raise _Stop
    return text.strip()


def _store(project_id: str, book_id: str, scene_id: str, text: str, start_version: int, start_empty: bool,
           run_id: str, model: str) -> str:
    """Leer und unverändert → direkt; sonst Vorschlag. Gibt den Zustand für den Fortschritt zurück."""
    if start_empty:
        try:
            storage.save_scene(project_id, book_id, scene_id, {"text": text, "origin": "ai_draft", "status": "draft"},
                               base_version=start_version)
            return "written"
        except Conflict:
            pass   # Autor hat die Szene inzwischen geändert → Vorschlag statt Überschreiben
    proposals.store(project_id, book_id, scene_id, text, run_id=run_id, model=model, base_version=start_version)
    return "proposal"


async def _scene(run_id: str, project_id: str, book_id: str, scene_id: str, opts: dict, model, limit: int,
                 used_out: int) -> tuple[str, int, int]:
    book = storage.get_book(project_id, book_id)
    scene = storage.get_scene(project_id, book_id, scene_id)
    iv = interview_material(project_id, book_id, opts["chapter_id"]) if opts.get("source") == "interview" else None
    if not scene["summary"].strip() and iv is None:
        return "skipped_no_summary", 0, 0
    start_empty = not scene["text"].strip()
    if not start_empty and opts.get("skip_filled", True):
        return "skipped_filled", 0, 0
    length, chunk = ghost.plan_lengths(book, opts.get("length_words") or None)
    material = ghost.build_material(project_id, book_id, scene_id, interview=iv)
    est = _cost.scene_estimate(material, length_words=length, chunk_words=chunk)
    if limit and used_out + est["output_tokens"] > limit:
        raise _Limit
    runs.update_run(run_id, current_scene=scene_id)
    runs.set_scene_state(run_id, scene_id, "writing")
    text = await _write(run_id, material, model=model, length=length, chunk=chunk)
    tin, tout = est["input_tokens"], _cost.tokens(text)
    runs.add_usage(run_id, tokens_in=tin, tokens_out=tout, cost_micros=_cost.cost_micros(model or "", tokens_in=tin,
                                                                                         tokens_out=tout))
    if not text:
        raise StoryError("llm_empty", 502)
    state = _store(project_id, book_id, scene_id, text, scene["version"], start_empty, run_id, model or "")
    return state, tout, len(text.split())


async def execute(run_id: str, project_id: str, book_id: str, user: str, lock_key=None) -> None:
    run = runs.get_run(project_id, book_id, run_id)
    opts = run["options"]
    status, error, used_out, current = "done", None, 0, None
    try:
        runs.update_run(run_id, status="running")
        limit = int(opts.get("limit_tokens") or ghost_of(storage.get_book(project_id, book_id))["limit_tokens"] or 0)
        model = run["model"] or None
        for p in run["progress"]:
            current = p["scene_id"]
            if run_id in _cancelled:
                raise _Stop
            state, out, words = await _scene(run_id, project_id, book_id, current, opts, model, limit, used_out)
            used_out += out
            runs.set_scene_state(run_id, current, state, **({"words": words} if words else {}))
            current = None
    except _Stop:
        status = "cancelled"
        if current:
            runs.set_scene_state(run_id, current, "waiting")
    except _Limit:
        status = "limit"
    except asyncio.CancelledError:
        status, error = "error", "Lauf wurde beendet"
        raise
    except Exception as exc:  # Lauf-Grenze: Fehler lesbar speichern, Prozess läuft weiter
        logger.warning("storyteller: Lauf %s fehlgeschlagen: %s", run_id, exc)
        status, error = "error", (str(exc)[:300] or exc.__class__.__name__)
        if current:
            runs.set_scene_state(run_id, current, "error")
    finally:
        runs.update_run(run_id, status=status, error=error, current_scene=None)
        _cancelled.discard(run_id)
        if lock_key is not None:
            ai.release(lock_key)


def start_background(run_id: str, project_id: str, book_id: str, user: str, lock_key) -> asyncio.Task:
    return asyncio.create_task(execute(run_id, project_id, book_id, user, lock_key=lock_key),
                               name=f"{runs.RUN_TASK_PREFIX}{run_id}")
