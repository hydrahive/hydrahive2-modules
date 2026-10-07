"""Lauf eines Team-Auftrags (T1e): eigene Sitzung für den Helfer, Kern-Runner durchlaufen lassen, Ergebnis festhalten.

Gleiches Muster wie die Zeitpläne des Kerns (``schedules/execution._run_direct_task``): Sitzung anlegen und
``runner.run`` bis zum Ende iterieren – ohne Chat. Was der Helfer ablegt (Hinweise, Vorschläge), landet über seine
Werkzeuge direkt am Buch; hier zählen nur Status, Zusammenfassung, Tokens und Kosten. Ein Task je Auftrag
(Name ``TASK_PREFIX + job_id``) – darüber erkennt die Bereinigung nach einem Neustart, was noch lebt.
"""
from __future__ import annotations

import asyncio
import logging

from . import team_jobs
from .team import jobs_catalog

logger = logging.getLogger(__name__)

TASK_PREFIX = "storyteller-job:"
TIMEOUT_SECONDS = 15 * 60
_EMBED = {"embedded_in": "storyteller"}


def _runner():
    from hydrahive.runner import runner
    return runner.run


def _cost(model: str, done) -> int | None:
    from hydrahive.llm._pricing import cost_micros, provider_from_model
    if not model:
        return None
    return cost_micros(provider_from_model(model), model, prompt_tokens=done.input_tokens,
                       completion_tokens=done.output_tokens, cache_read_tokens=done.cache_read_tokens,
                       cache_creation_tokens=done.cache_creation_tokens)


async def _drive(project_id: str, book_id: str, job: dict, agent: dict, task: str) -> None:
    from hydrahive.db import sessions as sessions_db
    from hydrahive.runner.concurrency import session_run_guard
    from hydrahive.runner.events import Done, Error, MessageStart, TextBlock, TextDelta
    label = jobs_catalog.get(job["job"]).label
    session = sessions_db.create(agent_id=agent["id"], user_id=job["user"], project_id=project_id,
                                 title=f"Storyteller-Auftrag: {label} – {job['place_title']}"[:200],
                                 metadata={"storyteller_job": job["id"], "storyteller_book": book_id, **_EMBED})
    team_jobs.set_running(project_id, book_id, job["id"], session_id=session.id)
    # Zusammenfassung = Text der LETZTEN Antwortrunde mit Text (Zwischensätze wie „Ich lese zuerst …“ nicht).
    rounds: list[str] = [""]
    done, error = None, ""
    async with session_run_guard(session.id):     # wie der Chat: kein zweiter Lauf auf derselben Sitzung
        async for ev in _runner()(session.id, task):
            if isinstance(ev, MessageStart):
                rounds.append("")
            elif isinstance(ev, TextDelta):
                rounds[-1] += ev.text
            elif isinstance(ev, TextBlock):       # ohne Streaming: ganzer Text der Runde auf einmal
                rounds[-1] = ev.text
            elif isinstance(ev, Done):
                done = ev
            elif isinstance(ev, Error):
                error = ev.message
    if error or done is None:
        team_jobs.finish(project_id, book_id, job["id"], status="error", error=error or "Lauf ohne Ergebnis beendet")
        return
    team_jobs.finish(project_id, book_id, job["id"], status="done", summary=next((r for r in reversed(rounds) if r.strip()), "").strip(),
                     tokens_in=done.input_tokens + done.cache_read_tokens + done.cache_creation_tokens,
                     tokens_out=done.output_tokens, cost_micros=_cost(agent.get("llm_model") or "", done))


async def execute(project_id: str, book_id: str, job_id: str, *, task: str) -> None:
    """Führt den Auftrag aus. Setzt immer einen Endzustand (auch bei Fehler, Zeitgrenze, Abbruch)."""
    from hydrahive.agents import config as agent_config
    try:
        job = team_jobs.get(project_id, book_id, job_id)
        if job["cancel_requested"]:
            team_jobs.finish(project_id, book_id, job_id, status="cancelled")
            return
        agent = agent_config.get(job["agent_id"])
        if agent is None:
            team_jobs.finish(project_id, book_id, job_id, status="error", error="Helfer nicht gefunden")
            return
        await asyncio.wait_for(_drive(project_id, book_id, job, agent, task), timeout=TIMEOUT_SECONDS)
    except TimeoutError:
        team_jobs.finish(project_id, book_id, job_id, status="error",
                         error=f"Zeitgrenze ({round(TIMEOUT_SECONDS / 60)} min) überschritten")
    except asyncio.CancelledError:
        team_jobs.finish(project_id, book_id, job_id, status="cancelled")
        raise
    except Exception as exc:  # noqa: BLE001 — Lauf-Grenze: Fehler lesbar speichern, Server läuft weiter
        logger.warning("storyteller: Team-Auftrag %s fehlgeschlagen: %s", job_id, exc)
        team_jobs.finish(project_id, book_id, job_id, status="error", error=str(exc)[:300] or exc.__class__.__name__)


def start(project_id: str, book_id: str, job_id: str, *, task: str) -> asyncio.Task:
    return asyncio.create_task(execute(project_id, book_id, job_id, task=task), name=f"{TASK_PREFIX}{job_id}")


def _task(job_id: str) -> asyncio.Task | None:
    return next((t for t in asyncio.all_tasks() if t.get_name() == f"{TASK_PREFIX}{job_id}" and not t.done()), None)


def cancel(project_id: str, book_id: str, job_id: str) -> bool:
    """Abbruch: Wunsch festhalten (falls der Lauf noch nicht begonnen hat) und laufenden Task stoppen."""
    team_jobs.request_cancel(project_id, book_id, job_id)
    task = _task(job_id)
    if task is not None:
        task.cancel()
    return True


def live_ids() -> set[str]:
    return {t.get_name().removeprefix(TASK_PREFIX) for t in asyncio.all_tasks()
            if not t.done() and t.get_name().startswith(TASK_PREFIX)}


async def recover_stale_jobs() -> int:
    """Aufträge ohne lebenden Lauf (Dienst neu gestartet) beenden – nur in Buch-Projekten (``metadata.storyteller``).

    Andere Projekte werden nicht angefasst (``story_root`` würde dort sonst Ordner anlegen). Ein kaputtes Buch hält die
    übrigen nicht auf."""
    from hydrahive.projects import config as project_config

    from ._book import books_dir
    await asyncio.sleep(0)
    live, n = live_ids(), 0
    for project in project_config.list_all():
        if not isinstance((project.get("metadata") or {}).get("storyteller"), dict):
            continue
        root = books_dir(project["id"])
        for d in sorted(root.iterdir()) if root.is_dir() else []:
            if not (d / "jobs").is_dir():
                continue
            try:
                n += team_jobs.mark_stale(project["id"], d.name, live_ids=live)
            except Exception:  # ein Buch darf die Bereinigung der anderen nicht verhindern
                logger.exception("storyteller: Team-Aufträge in %s/%s nicht bereinigt", project["id"], d.name)
    if n:
        logger.warning("storyteller: %d abgebrochene Team-Aufträge bereinigt", n)
    return n
