"""Deep-Research-Modul — Lauf-Persistenz + Ausführung.

Ein Lauf = eine Zeile in module_research_runs.
- start_run(): legt Lauf an (Status 'queued'), startet Hintergrund-Task, gibt run_id zurück
- run_blocking(): wartet bis fertig (für das Agent-Tool)
Eine globale Semaphore serialisiert die Ausführung (Such-Queue) — sinnvoll für lokale
Modelle, die nur einen Lauf gleichzeitig stemmen.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from hydrahive.db.connection import db

from .research import run_research
from .research.models import RunState

logger = logging.getLogger(__name__)

# ponytail: ein Lauf gleichzeitig (Queue). Auf >1 erhöhen, wenn Modell/Hardware es trägt.
_MAX_CONCURRENT = 1
_SEM = asyncio.Semaphore(_MAX_CONCURRENT)

_UPDATABLE = {"status", "category", "progress_json", "result_json", "error"}


def _row(r) -> dict[str, Any]:
    d = dict(r)
    d["progress"] = json.loads(d.pop("progress_json", None) or "{}")
    raw_result = d.pop("result_json", None)
    d["result"] = json.loads(raw_result) if raw_result else None
    return d


def create_run(username: str, question: str, model: str | None) -> dict[str, Any]:
    run_id = str(uuid.uuid4())
    with db() as c:
        c.execute(
            "INSERT INTO module_research_runs (id, username, question, model, status) "
            "VALUES (?, ?, ?, ?, 'queued')",
            (run_id, username, question, model or None),
        )
    return get_run(username, run_id)  # type: ignore[return-value]


def get_run(username: str, run_id: str) -> dict[str, Any] | None:
    with db() as c:
        row = c.execute(
            "SELECT * FROM module_research_runs WHERE id = ? AND username = ?",
            (run_id, username),
        ).fetchone()
    return _row(row) if row else None


def list_runs(username: str, limit: int = 50) -> list[dict[str, Any]]:
    with db() as c:
        rows = c.execute(
            "SELECT id, username, question, model, status, category, progress_json, "
            "NULL AS result_json, error, created_at, updated_at "
            "FROM module_research_runs WHERE username = ? ORDER BY created_at DESC LIMIT ?",
            (username, limit),
        ).fetchall()
    return [_row(r) for r in rows]


def delete_run(username: str, run_id: str) -> bool:
    with db() as c:
        cur = c.execute(
            "DELETE FROM module_research_runs WHERE id = ? AND username = ?",
            (run_id, username),
        )
        return cur.rowcount > 0


def _update(run_id: str, **fields: Any) -> None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with db() as c:
        c.execute(
            f"UPDATE module_research_runs SET {set_clause}, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
            [*fields.values(), run_id],
        )


async def _execute_run(
    run_id: str, question: str, model: str | None,
    max_rounds: int | None, category: str | None,
) -> None:
    state = RunState(question=question, model=model or None)

    def progress(p: dict) -> None:
        _update(run_id, status="running", progress_json=json.dumps(p), category=p.get("category", "general"))

    async with _SEM:   # Queue: wartet, bis ein Slot frei ist
        _update(run_id, status="running")
        try:
            result = await run_research(
                state, progress=progress, max_rounds=max_rounds or 6, category=category,
            )
            _update(
                run_id,
                status="done",
                category=result["category"],
                progress_json=json.dumps(result["stats"]),
                result_json=json.dumps(result, ensure_ascii=False),
            )
        except Exception as e:  # noqa: BLE001 - Lauf-Grenze: Fehler in die Zeile, nicht in den Loop
            logger.exception("deepresearch: Lauf %s fehlgeschlagen", run_id)
            _update(run_id, status="error", error=str(e))


async def start_run(
    username: str, question: str, model: str | None = None,
    max_rounds: int | None = None, category: str | None = None,
) -> str:
    run = create_run(username, question, model)
    asyncio.create_task(_execute_run(run["id"], question, model, max_rounds, category))
    return run["id"]


async def run_blocking(
    username: str, question: str, model: str | None = None,
    max_rounds: int | None = None, category: str | None = None,
) -> dict[str, Any]:
    run = create_run(username, question, model)
    await _execute_run(run["id"], question, model, max_rounds, category)
    return get_run(username, run["id"])  # type: ignore[return-value]
