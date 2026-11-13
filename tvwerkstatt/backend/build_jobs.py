"""Auftrag „Startbildschirm bauen“ (PLAN-E1.md Baustein 4).

Ablauf: Container an → Quelle am festen Commit holen → Gradle-Prüfsummen → Bau → App auswerten → Container anhalten
(Gradle lässt trotz --no-daemon einen Java-Prozess stehen, Probelauf 13.11.). Fortschritt im Auftrag (kind=build),
Ergebnis und Protokollende in module_tvwerkstatt_builds.
"""
from __future__ import annotations

import logging
import uuid

from hydrahive.containers.incus_client import IncusError
from hydrahive.db.connection import db

from . import build, container, incus, jobs, network, source, state

logger = logging.getLogger(__name__)
UID = "1000"
_TIMEOUTS = {"fetch": 600.0, "verify": 60.0, "build": 1800.0, "collect": 120.0}


async def _run(script: str, step: str) -> tuple[int, str, str]:
    """Skript als Bau-Nutzer (ohne sudo) im Container."""
    try:
        return await incus.run("exec", container.NAME, "--cwd", source.HOME, "--user", UID, "--group", UID, "--env",
                               f"HOME={source.HOME}", "--", "bash", "-c", script, timeout=_TIMEOUTS[step])
    except IncusError as exc:
        return 1, "", str(exc)


def _new_build(source_id: str) -> str:
    build_id = uuid.uuid4().hex[:12]
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_builds (build_id, source_id, part, commit_id, state) "
                     "VALUES (?, ?, ?, ?, 'running')", (build_id, source_id, source.PART, source.COMMIT))
        conn.commit()
    return build_id


def _set_build(build_id: str, **fields) -> None:
    sets = ", ".join(f"{k} = ?" for k in fields)
    with db() as conn:
        conn.execute(f"UPDATE module_tvwerkstatt_builds SET {sets} WHERE build_id = ?", (*fields.values(), build_id))
        conn.commit()


def interrupted_builds() -> None:
    """Bauten, die beim Neustart liefen, gelten als gescheitert (der Auftrag dazu wird ebenso markiert)."""
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_builds SET state = 'failed' WHERE state = 'running'")
        conn.commit()


async def run_build(job_id: str) -> None:
    step, build_id = "container", ""
    try:
        if await container.status() == "missing":
            raise build.TvwBuildError("tvw_not_set_up")
        await network.sync_rules(state.device_targets())
        await container.ensure_running()
        await container.wait_for_address()
        build_id = _new_build(source.source_id())
        for step, script, code in (("fetch", source.FETCH_SCRIPT, "tvw_source_failed"),
                                   ("verify", source.VERIFY_SCRIPT, "tvw_source_mismatch")):
            jobs.update(job_id, step=step)
            rc, out, err = await _run(script, step)
            if rc != 0:
                raise build.TvwBuildError("tvw_source_mismatch" if rc == source.RC_MISMATCH else code,
                                          build.clean_log(f"{out}\n{err}"))
        step = "build"
        jobs.update(job_id, step=step)
        rc, out, err = await _run(build.BUILD_SCRIPT, step)
        log = build.clean_log(f"{out}\n{err}")
        _set_build(build_id, log_tail=log)
        if rc != 0:
            raise build.TvwBuildError("tvw_build_failed", log)
        step = "collect"
        jobs.update(job_id, step=step)
        rc, out, err = await _run(build.COLLECT_SCRIPT, step)
        if rc != 0:
            raise build.TvwBuildError("tvw_build_unreadable", build.clean_log(err))
        info = build.evaluate(build.parse(out))
        _set_build(build_id, state="done", **info)
        jobs.finish(job_id)
    except (build.TvwBuildError, network.TvwNetworkError, container.TvwContainerError) as exc:
        if build_id:
            _set_build(build_id, state="failed")
        jobs.finish(job_id, error=exc.code, step=step, detail=getattr(exc, "detail", ""))
    except Exception:
        logger.exception("TV-Werkstatt: Bau gescheitert")
        if build_id:
            _set_build(build_id, state="failed")
        jobs.finish(job_id, error="tvw_build_failed", step=step)
    finally:
        try:
            await container.stop()
        except container.TvwContainerError:
            logger.warning("TV-Werkstatt: Container nach dem Bau nicht angehalten")
