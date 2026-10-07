"""Ghostwriter G2 – Lauf-Datensätze (Spec ghostwriter.md §9.2) und Bereinigung nach Neustart.

Ein Lauf gehört zu Projekt + Buch; gelesen wird immer mit beiden (fremde Projekte sehen nichts).
Läufe ohne lebenden asyncio-Task (Name ``storyteller-run:<id>``) werden nach einem Neustart als
„abgebrochen“ markiert – nach dem Muster von Deep Research.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from hydrahive.db.connection import db

logger = logging.getLogger(__name__)

RUN_TASK_PREFIX = "storyteller-run:"
MAX_RUN_SCENES = 200
ACTIVE = ("queued", "running")
_RESTART_ERROR = "Durch Neustart abgebrochen – bitte neu starten"
_UPDATABLE = {"status", "current_scene", "error"}


def _row(r) -> dict[str, Any]:
    d = dict(r)
    d["options"] = json.loads(d.pop("options_json") or "{}")
    d["progress"] = json.loads(d.pop("progress_json") or "[]")
    d["cost_partial"] = bool(d["cost_partial"])
    return d


def create_run(*, user: str, project_id: str, book_id: str, scope: str, scene_ids: list[str],
               model: str, options: dict) -> dict[str, Any]:
    if len(scene_ids) > MAX_RUN_SCENES:
        raise ValueError("too_many_scenes")
    run_id = uuid.uuid4().hex
    progress = [{"scene_id": s, "state": "waiting"} for s in scene_ids]
    with db() as c:
        c.execute(
            "INSERT INTO module_storyteller_runs (id, username, project_id, book_id, scope, model, options_json, "
            "progress_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, user, project_id, book_id, scope, model or "", json.dumps(options), json.dumps(progress)),
        )
    return get_run(project_id, book_id, run_id)  # type: ignore[return-value]


def get_run(project_id: str, book_id: str, run_id: str) -> dict[str, Any] | None:
    with db() as c:
        row = c.execute("SELECT * FROM module_storyteller_runs WHERE id = ? AND project_id = ? AND book_id = ?",
                        (run_id, project_id, book_id)).fetchone()
    return _row(row) if row else None


def _one(project_id: str, book_id: str, extra: str) -> dict[str, Any] | None:
    with db() as c:
        row = c.execute(f"SELECT * FROM module_storyteller_runs WHERE project_id = ? AND book_id = ? {extra} "
                        "ORDER BY created_at DESC, rowid DESC LIMIT 1", (project_id, book_id)).fetchone()
    return _row(row) if row else None


def active_run(project_id: str, book_id: str) -> dict[str, Any] | None:
    return _one(project_id, book_id, "AND status IN ('queued', 'running')")


def latest_run(project_id: str, book_id: str) -> dict[str, Any] | None:
    return _one(project_id, book_id, "")


def update_run(run_id: str, **fields: Any) -> None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with db() as c:
        c.execute(f"UPDATE module_storyteller_runs SET {sets}, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') "
                  "WHERE id = ?", [*fields.values(), run_id])


def set_scene_state(run_id: str, scene_id: str, state: str, **extra: Any) -> None:
    with db() as c:
        row = c.execute("SELECT progress_json FROM module_storyteller_runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return
        progress = json.loads(row["progress_json"] or "[]")
        for p in progress:
            if p["scene_id"] == scene_id:
                p.clear()
                p.update(scene_id=scene_id, state=state, **extra)
        c.execute("UPDATE module_storyteller_runs SET progress_json = ?, "
                  "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?", (json.dumps(progress), run_id))


def add_usage(run_id: str, *, tokens_in: int, tokens_out: int, cost_micros: int | None) -> None:
    """Tokens hochzählen. Kosten nur aus bekannten Tarifen; fehlt einer, wird ``cost_partial`` gesetzt."""
    with db() as c:
        c.execute(
            "UPDATE module_storyteller_runs SET tokens_in = tokens_in + ?, tokens_out = tokens_out + ?, "
            "cost_micros = CASE WHEN ? IS NULL THEN cost_micros ELSE COALESCE(cost_micros, 0) + ? END, "
            "cost_partial = CASE WHEN ? IS NULL THEN 1 ELSE cost_partial END, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            (tokens_in, tokens_out, cost_micros, cost_micros, cost_micros, run_id),
        )


def _live_run_ids() -> set[str]:
    return {t.get_name().removeprefix(RUN_TASK_PREFIX) for t in asyncio.all_tasks()
            if not t.done() and t.get_name().startswith(RUN_TASK_PREFIX)}


async def recover_stale_runs() -> int:
    """Läufe ohne lebenden Task (Dienst neu gestartet) als abgebrochen markieren."""
    await asyncio.sleep(0)
    live = sorted(_live_run_ids())
    where = "status IN ('queued', 'running')"
    if live:
        where += f" AND id NOT IN ({', '.join('?' for _ in live)})"
    with db() as c:
        cur = c.execute(f"UPDATE module_storyteller_runs SET status = 'error', error = ?, "
                        f"updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE {where}", [_RESTART_ERROR, *live])
    if cur.rowcount:
        logger.warning("storyteller: %d abgebrochene Ghostwriter-Läufe bereinigt", cur.rowcount)
    return cur.rowcount
