"""Serielle Ausfuehrung der Analysejobs.

E1 braucht keinen eigenen Dienst: ein Thread im Backend reicht. Die Jobs
liegen dauerhaft in SQLite, damit ein Neustart keine Analyse verliert.

Regeln:
- Immer nur eine Analyse gleichzeitig. So braucht der Container keine
  Parallelitaetssteuerung und die Last bleibt klein.
- Nach einem Neustart gilt ein `running`-Job als `interrupted`. Er wird nicht
  automatisch wiederholt, weil das Ergebnis vielleicht schon teilweise
  vorlag.
- Das Ergebnis wird als Datei im Fall abgelegt, nicht in der Datenbank.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from pathlib import Path

from . import store
from .files import cases_root
from .runtime import IncusRuntime, RuntimeError_

logger = logging.getLogger(__name__)


class JobRunner:
    """Fuehrt Analysejobs nacheinander aus."""

    def __init__(self, runtime=None):
        self._runtime = runtime or IncusRuntime()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # --- Lebenszyklus ----------------------------------------------------

    def recover(self) -> int:
        """Nach einem Neustart laufende Jobs als unterbrochen markieren."""
        return store.mark_interrupted_jobs()

    def start(self) -> None:
        """Worker-Thread starten, falls er nicht laeuft."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="zerlege-jobs",
                                            daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Worker-Thread beenden."""
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            job = store.next_queued_job()
            if not job:
                self._stop.wait(2.0)
                continue
            try:
                self.run_job(job["id"])
            except Exception:
                logger.exception("Analysejob %s fehlgeschlagen", job.get("id"))

    # --- Ein Job ---------------------------------------------------------

    def run_job(self, job_id: str) -> dict:
        """Einen Job ausfuehren und seinen Endzustand zurueckgeben."""
        job = store.get_job(job_id)
        if not job:
            raise ValueError("unknown job")
        if job["status"] not in ("queued", "running"):
            return job

        store.update_job(job_id, status="running", progress=10, error_code=None)
        try:
            payload = self._execute(job)
        except RuntimeError_ as error:
            store.update_job(job_id, status="failed", progress=0,
                             error_code=f"reverse_{error.code}")
            return store.get_job(job_id)  # type: ignore[return-value]
        except Exception:
            logger.exception("Analysejob %s unerwartet abgebrochen", job_id)
            store.update_job(job_id, status="failed", progress=0,
                             error_code="reverse_analysis_failed")
            return store.get_job(job_id)  # type: ignore[return-value]

        result_path = self._store_result(job, payload)
        store.update_job(job_id, status="done", progress=100,
                         result_path=result_path, error_code=None)
        return store.get_job(job_id)  # type: ignore[return-value]

    def _execute(self, job: dict) -> dict:
        """Analyse ausfuehren. Der Adapter arbeitet offline und begrenzt."""
        artifact = store.get_artifact(job["artifact_id"])
        if not artifact:
            raise RuntimeError_("artifact_missing")
        local = self._artifact_path(job["case_id"], artifact)
        token = uuid.uuid4().hex[:12]
        payload, _run = self._runtime.analyze(
            analysis_type=job["analysis_type"],
            artifact=local,
            artifact_kind=artifact["kind"],
            token=token,
        )
        return payload

    def _artifact_path(self, case_id: str, artifact: dict) -> Path:
        """Pfad des Artefakts im Fall. Der Name im Fall ist eine ID."""
        root = cases_root(case_id) / "input"
        return root / Path(str(artifact["relative_path"])).name

    def _store_result(self, job: dict, payload: dict) -> str:
        """Ergebnis als Datei im Fall ablegen und den relativen Pfad liefern."""
        results = cases_root(job["case_id"]) / "results"
        results.mkdir(parents=True, exist_ok=True)
        name = f"{job['id']}.json"
        target = results / name
        temporary = results / f".{name}.part"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(target)
        return f"results/{name}"


#: Ein Worker pro Backendprozess.
_runner: JobRunner | None = None
_runner_lock = threading.Lock()


def get_runner() -> JobRunner:
    """Gemeinsamen Worker liefern."""
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = JobRunner()
        return _runner
