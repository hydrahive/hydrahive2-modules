"""Auftrag „Werkstatt einrichten“ mit sichtbarem Schritt (PLAN-E1.md Baustein 3; Muster vibe/backend/jobs.py).

Ablauf: Netz + Sperrliste → Container an → Adresse → Einrichtung → Netzprobe → Container anhalten.
Zustand steht in module_tvwerkstatt_jobs (kind=setup). Es läuft höchstens ein Auftrag. Steht nach einem Neustart noch
ein Auftrag auf „running“, gilt er als unterbrochen (wird beim nächsten Lesen auf failed gesetzt).
"""
from __future__ import annotations

import logging
import uuid

from hydrahive.db.connection import db

from . import container, network, provision, state

logger = logging.getLogger(__name__)
_busy: set[str] = set()
_COLS = ("job_id", "state", "step", "error_code", "error_detail", "started_by", "created_at", "updated_at")
_NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


class JobError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def busy() -> bool:
    return bool(_busy)


def reset() -> None:
    _busy.clear()


def update(job_id: str, **fields: str) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    with db() as conn:
        conn.execute(f"UPDATE module_tvwerkstatt_jobs SET {sets}, updated_at = {_NOW} WHERE job_id = ?",
                     (*fields.values(), job_id))
        conn.commit()


def last_job(kind: str, target: str | None = None) -> dict | None:
    """Letzter Auftrag dieser Art (und dieses Ziels). „running“ ohne laufenden Auftrag hier → unterbrochen."""
    where, args = "kind = ?", [kind]
    if target is not None:
        where, args = where + " AND target = ?", [kind, target]
    with db() as conn:
        row = conn.execute(f"SELECT {', '.join(_COLS)} FROM module_tvwerkstatt_jobs WHERE {where} "
                           "ORDER BY created_at DESC, rowid DESC LIMIT 1", args).fetchone()
    if row is None:
        return None
    job = dict(zip(_COLS, row, strict=True))
    if job["state"] == "running" and job["job_id"] not in _busy:
        update(job["job_id"], state="failed", error_code="tvw_interrupted")
        job.update(state="failed", error_code="tvw_interrupted")
    return job


def last_setup() -> dict | None:
    return last_job("setup")


def begin(kind: str, target: str, admin: str, step: str) -> str:
    """Auftrag anlegen (vor dem Hintergrundlauf, damit die Seite ihn sofort sieht). Höchstens einer gleichzeitig."""
    if _busy:
        raise JobError("tvw_busy")
    job_id = uuid.uuid4().hex
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_jobs (job_id, kind, target, state, step, started_by) "
                     "VALUES (?, ?, ?, 'running', ?, ?)", (job_id, kind, target, step, admin))
        conn.commit()
    _busy.add(job_id)
    return job_id


def finish(job_id: str, *, error: str = "", step: str = "", detail: str = "") -> None:
    if error:
        update(job_id, state="failed", step=step, error_code=error, error_detail=detail[:600])
    else:
        update(job_id, state="done", step="done", error_code="", error_detail="")
    _busy.discard(job_id)


def begin_setup(admin: str, *, license_accepted: bool) -> str:
    if not license_accepted:
        raise JobError("tvw_license_required")
    return begin("setup", "android-sdk-license-accepted", admin, "network")


async def run_setup(job_id: str, *, start_at: str = "") -> None:
    """Der eigentliche Lauf. Fehler landen mit Code, Schritt und Ausgabe-Ende im Auftrag."""
    step = "network"
    try:
        tvs = state.device_targets()
        await network.ensure_network(tvs)
        step = "container"
        update(job_id, step=step)
        if await container.status() == "missing":
            start_at = ""                              # abgebaut: Weitermachen ginge ins Leere, also von vorn
        await container.ensure_running()
        await container.wait_for_address()

        def report(key: str) -> None:
            nonlocal step
            step = key
            update(job_id, step=key)
        await provision.setup(report, license_accepted=True, start_at=start_at)
        report("probe")
        await network.probe(container.NAME, await network.gateway(), tvs)
        report("stop")
        await container.stop()
    except provision.SetupError as exc:
        update(job_id, state="failed", step=exc.step or step, error_code=exc.code, error_detail=exc.detail)
        raise JobError(exc.code) from None
    except (network.TvwNetworkError, container.TvwContainerError) as exc:
        update(job_id, state="failed", step=step, error_code=exc.code)
        raise JobError(exc.code) from None
    except Exception:
        logger.exception("TV-Werkstatt: Einrichtung gescheitert")
        update(job_id, state="failed", step=step, error_code="tvw_setup_failed")
        raise JobError("tvw_setup_failed") from None
    else:
        update(job_id, state="done", step="done", error_code="", error_detail="")
    finally:
        _busy.discard(job_id)


def retry_step() -> str:
    """Ab welchem Einrichtungsschritt „Nochmal versuchen“ beginnt (nur Schritte der Einrichtung, sonst von vorn)."""
    job = last_setup()
    keys = {s.key for s in provision.STEPS}
    return job["step"] if job and job["state"] == "failed" and job["step"] in keys else ""
