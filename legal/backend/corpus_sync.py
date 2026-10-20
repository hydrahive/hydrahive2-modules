"""Abgleich des Gesetzeskorpus (Plan L1 Schritt 5): Kernliste + nachgeladene Gesetze, täglich.

- Ein Fehler bei einem Gesetz bricht den Lauf nicht ab; Fehler stehen im Protokoll (``module_legal_sync``).
- Höflich zum Server: Pause zwischen den Abrufen (L0: 54 Gesetze in 33 s mit 0,5 s Pause).
- Nur ein Lauf gleichzeitig (Job und Admin-Knopf).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from hydrahive.db.connection import db

from . import corpus_list, corpus_store, gii_fetch
from .gii_parse import GiiParseError, parse_law

logger = logging.getLogger(__name__)

PAUSE_SECONDS = 0.5
DUE_AFTER_HOURS = 20
_RUNNING = False


class SyncBusy(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def is_due(last_finished: str | None, *, now: str | None = None) -> bool:
    if not last_finished:
        return True
    return (_parse(now or _now()) - _parse(last_finished)).total_seconds() >= DUE_AFTER_HOURS * 3600


def last_run() -> dict | None:
    with db() as c:
        row = c.execute("SELECT id, started_at, finished_at, state, laws_total, laws_changed, errors "
                        "FROM module_legal_sync ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    return {"id": row[0], "started_at": row[1], "finished_at": row[2], "state": row[3], "total": row[4],
            "changed": row[5], "errors": json.loads(row[6] or "[]")}


def keys_to_sync() -> list[str]:
    """Kernliste + alle bereits geladenen (nachgeladenen) Gesetze, ohne Doppel."""
    loaded = [law["key"] for law in corpus_store.list_laws()]
    return list(dict.fromkeys(corpus_list.core_keys() + loaded))


async def run(keys: list[str]) -> dict:
    global _RUNNING
    if _RUNNING:
        raise SyncBusy("Abgleich läuft bereits")
    _RUNNING = True
    started = _now()
    with db() as c:
        run_id = c.execute("INSERT INTO module_legal_sync(started_at, state, laws_total) VALUES (?, 'running', ?)",
                           (started, len(keys))).lastrowid
    changed, errors = 0, []
    core = set(corpus_list.core_keys())
    try:
        for i, key in enumerate(keys):
            try:
                xml = await gii_fetch.fetch_law_xml(key)
                law = parse_law(key, xml)
                res = corpus_store.save_law(law, xml, fetched_at=_now(), pinned=key in core)
                changed += int(res["changed"])
            except (gii_fetch.FetchError, GiiParseError) as e:
                errors.append({"key": key, "error": str(e)[:200]})
                logger.warning("Recht: Abgleich %s fehlgeschlagen: %s", key, e)
            if PAUSE_SECONDS and i + 1 < len(keys):
                await asyncio.sleep(PAUSE_SECONDS)
        state = "done"
    except Exception:
        state = "failed"
        logger.exception("Recht: Abgleich abgebrochen")
        raise
    finally:
        with db() as c:
            c.execute("UPDATE module_legal_sync SET finished_at = ?, state = ?, laws_changed = ?, errors = ? "
                      "WHERE id = ?", (_now(), state, changed, json.dumps(errors, ensure_ascii=False), run_id))
        _RUNNING = False
    logger.info("Recht: Abgleich fertig – %d Gesetze, %d geändert, %d Fehler", len(keys), changed, len(errors))
    return {"total": len(keys), "changed": changed, "errors": errors}


async def job() -> None:
    """Modul-Job (stündlich geprüft): läuft, wenn der letzte fertige Lauf älter als 20 h ist oder es keinen gibt."""
    last = last_run()
    if last and last["state"] == "running":
        return
    if not is_due(last["finished_at"] if last else None):
        return
    try:
        await run(keys_to_sync())
    except SyncBusy:
        pass
