"""Miner-Prozess führen: starten, stoppen, beobachten, messen, Watchdog.

Je Hersteller-Gruppe höchstens ein Miner. ``apply(desired)`` wird nach jeder Meldung
aufgerufen und gleicht ab. ``tick()`` liefert den Zustand für die nächste
Meldung (inkl. fertigem Benchmark-Ergebnis, das danach verworfen wird).

Watchdog: Prozess tot oder Hashrate > ``STALL_SECONDS`` lang 0 → Neustart.
Nach ``MAX_RESTARTS`` Fehlschlägen in Folge wird der Auftrag als kaputt
gemeldet (``failed``) und nicht mehr gestartet, bis ein anderer kommt.
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path

from . import catalog, fetch, minerapi

logger = logging.getLogger("hydrahive_rig")
WARMUP_SECONDS = 60     # DAG-Aufbau etc. — so lange keine Hashrate erwarten
STALL_SECONDS = 180
MAX_RESTARTS = 3


class Runner:
    def __init__(self, state_dir: Path, vendor: str, *, group: str | None = None, mixed: bool = False,
                 clock=time.monotonic, spawn=subprocess.Popen, ensure=fetch.ensure, read_api=minerapi.read) -> None:
        self.state_dir, self.vendor = state_dir, vendor
        self.group, self.mixed = group or vendor, mixed
        self._clock, self._spawn, self._ensure, self._read = clock, spawn, ensure, read_api
        self.proc = None
        self.key = None            # (action, coin, miner)
        self.spec = None
        self.started = 0.0
        self.last_hash_at = 0.0
        self.restarts = 0
        self.failed_key = None
        self.error = None
        self.bench_until = 0.0
        self.samples: list[float] = []
        self.bench_result = None
        self.last = {"hashrate": None, "accepted": 0, "rejected": 0, "watts": None}

    # ---- Abgleich ----
    def apply(self, desired: dict) -> None:
        action = desired.get("action")
        if action not in ("mine", "benchmark"):
            self.stop()
            self.key, self.failed_key = None, None
            return
        job = desired.get("job") or {}
        key = (action, job.get("coin"), job.get("miner"))
        if key == self.failed_key:
            return                                    # kaputt gemeldet, warten auf neuen Auftrag
        if key == self.key and self.proc is not None:
            return
        try:
            spec = catalog.build(job, self.vendor, mixed=self.mixed, group=self.group)
        except catalog.JobError as exc:
            self._fail(key, f"job_rejected:{exc}")
            return
        self.stop()
        self.key, self.spec, self.restarts, self.error = key, spec, 0, None
        if action == "benchmark":
            self.bench_until = self._clock() + max(60, min(int(desired.get("seconds") or 180), 900))
            self.samples, self.bench_result = [], None
        self._start()

    def _start(self) -> None:
        try:
            exe = self._ensure(self.spec["miner"], self.state_dir)
        except (fetch.FetchError, OSError) as exc:
            self._fail(self.key, f"fetch:{exc}")
            return
        log = (self.state_dir / ("miner.log" if not self.mixed else f"miner-{self.group}.log")).open("ab")
        self.proc = self._spawn([str(exe), *self.spec["args"]], stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, cwd=str(exe.parent), start_new_session=True)
        self.started = self.last_hash_at = self._clock()
        logger.info("Miner gestartet: %s %s (%s)", self.spec["miner"], self.spec["algo"], self.key[0])

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            os.killpg(self.proc.pid, signal.SIGTERM)
            self.proc.wait(timeout=15)
        except (ProcessLookupError, PermissionError):
            pass
        except subprocess.TimeoutExpired:
            os.killpg(self.proc.pid, signal.SIGKILL)
            self.proc.wait(timeout=5)
        self.proc = None

    def _fail(self, key, error: str) -> None:
        self.stop()
        self.failed_key, self.key, self.error = key, None, error
        logger.error("Miner-Auftrag aufgegeben: %s (%s)", key, error)
        if key and key[0] == "benchmark":
            self.bench_result = {"coin": key[1], "miner": key[2], "hashrate": None, "error": error}

    # ---- Beobachten ----
    def tick(self, gpu_watts: float | None) -> dict:
        now = self._clock()
        if self.proc is not None:
            api = self._read(self.spec["api"], self.spec.get("api_port", catalog.API_PORT)) or {}
            if api:
                self.last = {**self.last, **{k: v for k, v in api.items() if v is not None}}
                self.last["hashrate"] = api.get("hashrate")
            if self.last.get("hashrate"):
                self.last_hash_at = now
            dead = self.proc.poll() is not None
            stalled = now - self.started > WARMUP_SECONDS and now - self.last_hash_at > STALL_SECONDS
            if dead or stalled:
                self._watchdog("exited" if dead else "no_hashrate")
            elif self.key and self.key[0] == "benchmark":
                self._bench_step(now, gpu_watts)
        state = {"miner": self.key[0] if self.key and self.proc else "idle",
                 "job": {"coin": self.key[1], "miner": self.key[2]} if self.key else None,
                 "hashrate": self.last.get("hashrate") if self.proc else None,
                 "accepted": self.last.get("accepted"), "rejected": self.last.get("rejected"),
                 "error": self.error, "restarts": self.restarts}
        if self.bench_result is not None:
            state["benchmark_result"], self.bench_result = self.bench_result, None
        return state

    def _watchdog(self, why: str) -> None:
        self.restarts += 1
        logger.warning("Watchdog: %s (%s), Neustart %d/%d", self.spec["miner"], why, self.restarts, MAX_RESTARTS)
        if self.restarts >= MAX_RESTARTS:
            self._fail(self.key, f"watchdog:{why}")
            return
        self.stop()
        self._start()

    def _bench_step(self, now: float, gpu_watts: float | None) -> None:
        hr = self.last.get("hashrate")
        if hr and now - self.started > WARMUP_SECONDS:
            self.samples.append(hr)
        if now >= self.bench_until:
            tail = self.samples[len(self.samples) // 2:] or self.samples
            value = sorted(tail)[len(tail) // 2] if tail else None   # Median der zweiten Hälfte
            self.bench_result = {"coin": self.key[1], "miner": self.key[2], "hashrate": value,
                                 "watts": self.last.get("watts") or gpu_watts,
                                 "error": None if value else "no_hashrate"}
            logger.info("Benchmark %s/%s: %s H/s", self.key[1], self.key[2], value)
            self.stop()
            self.key = None
