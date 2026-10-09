"""Ghostwriter G2 – Lauf im Hintergrund (Spec ghostwriter.md §9.2–§9.4).

Je Szene: Material (mit dem aktuellen Gedächtnis) → schreiben in Abschnitten (ghost.write_scene) →
ablegen. Ablegen nie still überschreibend: leer UND unverändert seit dem Start → direkt in die Szene
(ai_draft); sonst abgelegter Vorschlag (proposals.py). Abbrechen beendet den laufenden Modellaufruf.
Vor jeder Szene wird die Kostengrenze geprüft (Eingabe + Ausgabe, Spec kostengrenze.md §4). Die KI-Sperre des Buchs
wird in jedem Fall freigegeben. A4: Gedächtnis einmal je Lauf (ghost.MemoryIndex), Dateiarbeit im Hilfs-Thread.
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
    """Nächste Szene würde die Kostengrenze überschreiten (bisher verbraucht + Schätzung, Eingabe + Ausgabe)."""


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
           run_id: str, model: str) -> tuple[str, dict]:
    """Leer und unverändert → direkt; sonst Vorschlag. Gibt (Zustand, Zusatz für den Fortschritt) zurück –
    ersetzt der Vorschlag einen offenen (A2), steht dessen Herkunft in ``replaced``."""
    if start_empty:
        try:
            storage.save_scene(project_id, book_id, scene_id, {"text": text, "origin": "ai_draft", "status": "draft"},
                               base_version=start_version)
            return "written", {}
        except Conflict:
            pass   # Autor hat die Szene inzwischen geändert → Vorschlag statt Überschreiben
    p = proposals.store(project_id, book_id, scene_id, text, run_id=run_id, model=model, base_version=start_version)
    return "proposal", ({"replaced": p["replaced_from"]["author"]} if p["replaced_from"] else {})


def _prepare(run_id: str, project_id: str, book_id: str, scene_id: str, opts: dict, limit: int, used: int,
             index: ghost.MemoryIndex):
    """Dateiarbeit vor dem Schreiben (im Hilfs-Thread, A4). Gibt einen Zustand zum Überspringen zurück oder das
    vorbereitete Material."""
    book = index.book
    scene = storage.get_scene(project_id, book_id, scene_id)
    iv = interview_material(project_id, book_id, opts["chapter_id"]) if opts.get("source") == "interview" else None
    if not scene["summary"].strip() and iv is None:
        return "skipped_no_summary"
    start_empty = not scene["text"].strip()
    if not start_empty and opts.get("skip_filled", True):
        return "skipped_filled"
    length, chunk = ghost.plan_lengths(book, opts.get("length_words") or None)
    material = ghost.build_material(project_id, book_id, scene_id, interview=iv, index=index)
    est = _cost.scene_estimate(material, length_words=length, chunk_words=chunk)
    if limit and used + est["input_tokens"] + est["output_tokens"] > limit:
        raise _Limit
    runs.update_run(run_id, current_scene=scene_id)
    runs.set_scene_state(run_id, scene_id, "writing")
    return {"scene": scene, "start_empty": start_empty, "length": length, "chunk": chunk, "material": material, "est": est}


def _finish(run_id: str, project_id: str, book_id: str, scene_id: str, prep: dict, text: str, model,
            index: ghost.MemoryIndex) -> tuple[str, int, dict]:
    """Dateiarbeit nach dem Schreiben (im Hilfs-Thread): Kosten, Ablegen, Gedächtnis nachziehen."""
    tin, tout = prep["est"]["input_tokens"], _cost.tokens(text)
    runs.add_usage(run_id, tokens_in=tin, tokens_out=tout, cost_micros=_cost.cost_micros(model or "", tokens_in=tin,
                                                                                         tokens_out=tout))
    if not text:
        raise StoryError("llm_empty", 502)
    state, extra = _store(project_id, book_id, scene_id, text, prep["scene"]["version"], prep["start_empty"], run_id,
                          model or "")
    index.refresh(scene_id)   # die nächste Szene sieht Ende und Stand dieser (A4)
    return state, tin + tout, {"words": len(text.split()), **extra}


async def _scene(run_id: str, project_id: str, book_id: str, scene_id: str, opts: dict, model, limit: int,
                 used: int, index: ghost.MemoryIndex) -> tuple[str, int, dict]:
    """Gibt (Zustand, verbrauchte Tokens Eingabe + Ausgabe, Zusatz für den Fortschritt) zurück. Dateiarbeit läuft im
    Hilfs-Thread (der Server bleibt ansprechbar), nur das Schreiben mit dem Modell in der Ereignisschleife."""
    prep = await asyncio.to_thread(_prepare, run_id, project_id, book_id, scene_id, opts, limit, used, index)
    if isinstance(prep, str):
        return prep, 0, {}
    text = await _write(run_id, prep["material"], model=model, length=prep["length"], chunk=prep["chunk"])
    return await asyncio.to_thread(_finish, run_id, project_id, book_id, scene_id, prep, text, model, index)


async def execute(run_id: str, project_id: str, book_id: str, user: str, lock_key=None) -> None:
    run = await asyncio.to_thread(runs.get_run, project_id, book_id, run_id)
    opts = run["options"]
    status, error, used, current, killed = "done", None, 0, None, False
    try:
        await asyncio.to_thread(runs.update_run, run_id, status="running")
        index = await asyncio.to_thread(ghost.MemoryIndex.load, project_id, book_id)   # Gedächtnis einmal je Lauf
        limit = int(opts.get("limit_tokens") or ghost_of(index.book)["limit_tokens"] or 0)
        model = run["model"] or None
        for p in run["progress"]:
            current = p["scene_id"]
            if run_id in _cancelled:
                raise _Stop
            state, spent, extra = await _scene(run_id, project_id, book_id, current, opts, model, limit, used, index)
            used += spent
            await asyncio.to_thread(runs.set_scene_state, run_id, current, state, **extra)
            current = None
    except _Stop:
        status = "cancelled"
        if current:
            await asyncio.to_thread(runs.set_scene_state, run_id, current, "waiting")
    except _Limit:
        status = "limit"
    except asyncio.CancelledError:
        status, error, killed = "error", "Lauf wurde beendet", True
        raise
    except Exception as exc:  # Lauf-Grenze: Fehler lesbar speichern, Prozess läuft weiter
        logger.warning("storyteller: Lauf %s fehlgeschlagen: %s", run_id, exc)
        status, error = "error", (str(exc)[:300] or exc.__class__.__name__)
        if current:
            await asyncio.to_thread(runs.set_scene_state, run_id, current, "error")
    finally:
        try:
            # Endstatus unbedingt schreiben. Wurde der Task selbst abgebrochen, kein await mehr (direkt schreiben).
            if killed:
                runs.update_run(run_id, status=status, error=error, current_scene=None)
            else:
                await asyncio.to_thread(runs.update_run, run_id, status=status, error=error, current_scene=None)
        finally:
            _cancelled.discard(run_id)
            if lock_key is not None:
                ai.release(lock_key)


def start_background(run_id: str, project_id: str, book_id: str, user: str, lock_key) -> asyncio.Task:
    return asyncio.create_task(execute(run_id, project_id, book_id, user, lock_key=lock_key),
                               name=f"{runs.RUN_TASK_PREFIX}{run_id}")
