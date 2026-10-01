"""Bereinigt Deep-Research-Läufe ohne lebenden asyncio-Task."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

RUN_TASK_PREFIX = "deepresearch-run:"
_RESTART_ERROR = "Durch Neustart abgebrochen – bitte neu starten"


def _active_run_ids() -> set[str]:
    """Findet auch Tasks, die vor einem Modul-Reload gestartet wurden."""
    active: set[str] = set()
    for task in asyncio.all_tasks():
        if task.done():
            continue
        if task.get_name().startswith(RUN_TASK_PREFIX):
            active.add(task.get_name().removeprefix(RUN_TASK_PREFIX))

        awaited = task.get_coro()
        seen: set[int] = set()
        while awaited is not None and id(awaited) not in seen:
            seen.add(id(awaited))
            frame = getattr(awaited, "cr_frame", None) or getattr(awaited, "gi_frame", None)
            if frame and frame.f_code.co_name == "_execute_run":
                module_name = frame.f_globals.get("__name__", "")
                run_id = frame.f_locals.get("run_id")
                if module_name.endswith(".service") and isinstance(run_id, str):
                    active.add(run_id)
            awaited = getattr(awaited, "cr_await", None) or getattr(
                awaited, "gi_yieldfrom", None,
            )
    return active


def _mark_stale_runs(active_run_ids: set[str]) -> int:
    where = "status IN ('queued', 'running')"
    params: list[Any] = [_RESTART_ERROR]
    if active_run_ids:
        placeholders = ", ".join("?" for _ in active_run_ids)
        where += f" AND id NOT IN ({placeholders})"
        params.extend(sorted(active_run_ids))
    with db() as connection:
        cursor = connection.execute(
            "UPDATE module_research_runs SET status = 'error', error = ?, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') "
            f"WHERE {where}",
            params,
        )
    if cursor.rowcount:
        logger.warning("deepresearch: %d abgebrochene Läufe bereinigt", cursor.rowcount)
    return cursor.rowcount


async def recover_stale_runs() -> int:
    """Beendet persistierte Läufe, denen in diesem Prozess kein Task gehört."""
    await asyncio.sleep(0)
    return _mark_stale_runs(_active_run_ids())
