"""Aufträge aus den Team-Knöpfen (T1e, Plan schreib-team-t1e.md) – Ablage am Buch.

``storyteller/books/<id>/jobs/<job-id>.json``, eine Datei je Auftrag. Status nur vorwärts:
``queued → running → done | error | cancelled | limit`` (aus ``queued`` auch direkt in einen Endzustand).
``limit_tokens``: Kostengrenze dieses Auftrags (Eingabe + Ausgabe, 0 = aus), beim Start festgelegt (A1). Ein Helfer hat je Buch
höchstens einen aktiven Auftrag, je Buch laufen höchstens ``MAX_ACTIVE``. Ältere Endzustände werden auf ``KEEP``
gekürzt. Alles Ändernde unter der Sperre des Buchs.
"""
from __future__ import annotations

from typing import Any

from ._book import _existing, _now
from ._files import StoryError, check_id, inside, new_id, read_json, write_json
from ._ghost_settings import valid_limit
from ._locks import locked

ACTIVE = ("queued", "running")
ENDS = ("done", "error", "cancelled", "limit")
MAX_ACTIVE = 3
KEEP = 30
RESTART_ERROR = "Server neu gestartet – Auftrag abgebrochen"
_FIELDS = {"job": 40, "role": 40, "agent_id": 64, "agent_name": 200, "place_id": 64, "place_title": 200, "user": 100}


def _dir(project_id: str, book_id: str):
    return _existing(project_id, book_id) / "jobs"


def _path(project_id: str, book_id: str, job_id: str):
    return inside(_dir(project_id, book_id), f"{check_id(job_id, 'job')}.json")


def _read(path) -> dict:
    return {"limit_tokens": 0, **read_json(path)}   # Aufträge vor A1 ohne Grenze


def _all(project_id: str, book_id: str) -> list[dict]:
    d = _dir(project_id, book_id)
    return sorted((_read(p) for p in d.glob("*.json")), key=lambda j: j["seq"], reverse=True) if d.is_dir() else []


def _trim(project_id: str, book_id: str, jobs: list[dict]) -> None:
    ended = [j for j in jobs if j["status"] in ENDS]
    for j in ended[max(0, KEEP - (len(jobs) - len(ended))):]:
        _path(project_id, book_id, j["id"]).unlink(missing_ok=True)


@locked
def create(project_id: str, book_id: str, data: dict[str, Any]) -> dict:
    limit = valid_limit(data.get("limit_tokens", 0))
    jobs = _all(project_id, book_id)
    active = [j for j in jobs if j["status"] in ACTIVE]
    if any(j["agent_id"] == data.get("agent_id") for j in active):
        raise StoryError("job_busy", 409)
    if len(active) >= MAX_ACTIVE:
        raise StoryError("too_many_jobs", 429)
    now = _now()
    job = {"id": new_id(), "seq": max((j["seq"] for j in jobs), default=0) + 1,
           **{k: str(data.get(k) or "")[:n] for k, n in _FIELDS.items()},
           "estimate_micros": data.get("estimate_micros"), "limit_tokens": limit, "status": "queued", "session_id": "",
           "cancel_requested": False, "summary": "", "error": "", "tokens_in": 0, "tokens_out": 0,
           "cost_micros": None, "at": now, "updated_at": now, "finished_at": ""}
    write_json(inside(_dir(project_id, book_id), f"{job['id']}.json"), job)
    _trim(project_id, book_id, [job, *jobs])
    return job


def get(project_id: str, book_id: str, job_id: str) -> dict:
    path = _path(project_id, book_id, job_id)
    if not path.is_file():
        raise StoryError("job_not_found", 404)
    return _read(path)


def list_jobs(project_id: str, book_id: str) -> list[dict]:
    return _all(project_id, book_id)


def _save(project_id: str, book_id: str, job: dict) -> dict:
    job["updated_at"] = _now()
    write_json(_path(project_id, book_id, job["id"]), job)
    return job


@locked
def set_running(project_id: str, book_id: str, job_id: str, *, session_id: str) -> dict:
    job = get(project_id, book_id, job_id)
    if job["status"] != "queued":
        raise StoryError("job_not_active", 409)
    return _save(project_id, book_id, {**job, "status": "running", "session_id": session_id})


@locked
def finish(project_id: str, book_id: str, job_id: str, *, status: str, summary: str = "", error: str = "",
           tokens_in: int = 0, tokens_out: int = 0, cost_micros: int | None = None) -> dict:
    if status not in ENDS:
        raise StoryError("status_invalid")
    job = get(project_id, book_id, job_id)
    if job["status"] in ENDS:
        return job                               # Endzustand bleibt (z. B. Abbruch kam vor dem Ergebnis an)
    return _save(project_id, book_id, {**job, "status": status, "summary": summary[:2000], "error": error[:500],
                                       "tokens_in": int(tokens_in), "tokens_out": int(tokens_out),
                                       "cost_micros": cost_micros, "finished_at": _now()})


@locked
def request_cancel(project_id: str, book_id: str, job_id: str) -> dict:
    job = get(project_id, book_id, job_id)
    if job["status"] not in ACTIVE:
        raise StoryError("job_not_active", 409)
    return _save(project_id, book_id, {**job, "cancel_requested": True})


@locked
def mark_stale(project_id: str, book_id: str, *, live_ids: set[str]) -> int:
    """Aktive Aufträge ohne lebenden Lauf (Dienst neu gestartet) beenden. Anzahl zurück."""
    n = 0
    for job in _all(project_id, book_id):
        if job["status"] in ACTIVE and job["id"] not in live_ids:
            _save(project_id, book_id, {**job, "status": "error", "error": RESTART_ERROR, "finished_at": _now()})
            n += 1
    return n
