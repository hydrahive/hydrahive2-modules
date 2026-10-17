"""Aufträge des Studios (Spec „Bauplan Etappe 3“): eine Datei je Auftrag unter studio/jobs/, Ausführung im Hintergrund.

Ein Auftrag je Ziel (Shot) gleichzeitig. Die Arbeit läuft in einem Daemon-Thread, damit langsame Anbieter weder die
Anfrage noch den Server blockieren. Aufträge, die beim Neustart mitten im Lauf waren, werden als `interrupted` markiert.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone

from . import plan
from ._store import is_id, new_id, read_json, root, write_json

logger = logging.getLogger("hhmod_studio.jobs")

KEEP = 50                                   # so viele erledigte Aufträge je Projekt behalten
_lock = threading.Lock()
_running: set[tuple[str, str]] = set()      # (Projekt, Ziel)


class JobFailed(RuntimeError):
    """Fehlercode für den Auftrag (z. B. no_key, bad_image)."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir(pid: str):
    return root(pid) / "jobs"


def _save(pid: str, job: dict) -> None:
    write_json(root(pid, create=True) / "jobs" / f"{job['id']}.json", job)


def list_jobs(pid: str) -> list[dict]:
    d = _dir(pid)
    out = []
    for f in d.glob("*.json") if d.is_dir() else []:
        data = read_json(f, None)
        if is_id(f.stem) and isinstance(data, dict):
            out.append({**data, "id": f.stem})
    return sorted(out, key=lambda j: j.get("created_at") or "", reverse=True)


def _prune(pid: str) -> None:
    finished = [j for j in list_jobs(pid) if j.get("status") in ("done", "failed")]
    for j in finished[KEEP:]:
        (_dir(pid) / f"{j['id']}.json").unlink(missing_ok=True)


def start(pid: str, kind: str, target: str, scene_id: str, work: Callable[[], dict]) -> dict:
    """Auftrag anlegen und im Hintergrund ausführen. `work` liefert das Ergebnis (dict) oder wirft JobFailed."""
    with _lock:
        if (pid, target) in _running:
            raise plan.PlanError("studio_job_running", 409)
        _running.add((pid, target))
    job = {"id": new_id(), "kind": kind, "target": target, "scene_id": scene_id, "status": "running",
           "error": None, "result": None, "created_at": _now(), "finished_at": None}
    try:
        _save(pid, job)
    except Exception:
        with _lock:
            _running.discard((pid, target))
        raise

    def run() -> None:
        try:
            job["result"] = work()
            job["status"] = "done"
        except JobFailed as e:
            job["status"], job["error"] = "failed", str(e)
        except Exception:
            logger.exception("Studio-Auftrag %s (%s) fehlgeschlagen", job["id"], kind)
            job["status"], job["error"] = "failed", "internal"
        finally:
            job["finished_at"] = _now()
            try:
                _save(pid, job)
                _prune(pid)
            finally:
                with _lock:
                    _running.discard((pid, target))

    threading.Thread(target=run, name=f"studio-{kind}-{target[:8]}", daemon=True).start()
    return job


def recover(pid: str) -> int:
    """Nach einem Neustart: laufende Aufträge ohne Thread als abgebrochen markieren. Gibt die Anzahl zurück.

    Ein Video, das so abbricht, ließ den Shot sonst ewig auf „Video läuft“ stehen – der Shot wird mit zurückgesetzt."""
    n = 0
    for j in list_jobs(pid):
        if j.get("status") in ("running", "queued") and (pid, j.get("target")) not in _running:
            _save(pid, {**j, "status": "failed", "error": "interrupted", "finished_at": _now()})
            if j.get("kind") == "video":
                _reset_video_shot(pid, j.get("scene_id"), j.get("target"))
            n += 1
    return n


def _reset_video_shot(pid: str, scene_id, shot_id) -> None:
    from . import shots
    try:
        scene = shots.load_scene(pid, scene_id)
    except plan.PlanError:
        return
    items = list(scene.get("shots") or [])
    for i, s in enumerate(items):
        if isinstance(s, dict) and s.get("id") == shot_id and s.get("status") == "video_processing":
            items[i] = {**s, "status": "failed"}
            shots.save_shots(pid, scene, items)
            return
