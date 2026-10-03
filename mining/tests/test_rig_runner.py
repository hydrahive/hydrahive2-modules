"""Rig-Client E3: Runner, Watchdog, Benchmark."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import fetch, runner

JOB = {"coin": "rvn", "miner": "rigel", "algo": "kawpow", "user": "krxXJK8JJW", "worker": "till-wks", "region": "eu"}


# ---- Runner ----
class FakeProc:
    def __init__(self):
        self.pid, self.rc = 4711, None

    def poll(self):
        return self.rc

    def wait(self, timeout=None):
        return 0


class Harness:
    def __init__(self, tmp_path, monkeypatch):
        self.t, self.api, self.spawned = 1000.0, None, []
        monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: None)
        self.r = runner.Runner(tmp_path, "nvidia", clock=lambda: self.t, spawn=self._spawn,
                               ensure=lambda name, d: tmp_path / "bin" / name, read_api=lambda kind, port: self.api)

    def _spawn(self, argv, **kw):
        self.spawned.append(argv)
        return FakeProc()


@pytest.fixture
def h(tmp_path, monkeypatch):
    return Harness(tmp_path, monkeypatch)


def test_runner_starts_once_and_stops(h):
    h.r.apply({"action": "mine", "job": JOB})
    h.r.apply({"action": "mine", "job": JOB})
    assert len(h.spawned) == 1 and h.spawned[0][1:3] == ["-a", "kawpow"]
    h.r.apply({"action": "stop"})
    assert h.r.proc is None


def test_runner_rejects_foreign_job_without_starting(h):
    h.r.apply({"action": "mine", "job": {**JOB, "miner": "evil"}})
    assert h.spawned == [] and h.r.error.startswith("job_rejected")


def test_watchdog_restarts_dead_miner_then_gives_up(h):
    h.r.apply({"action": "mine", "job": JOB})
    for _ in range(runner.MAX_RESTARTS):
        h.r.proc.rc = 1
        h.r.tick(None)
    assert len(h.spawned) == runner.MAX_RESTARTS and h.r.proc is None and h.r.error == "watchdog:exited"
    h.r.apply({"action": "mine", "job": JOB})            # gleicher kaputter Auftrag → nicht neu starten
    assert len(h.spawned) == runner.MAX_RESTARTS


def test_watchdog_stall_only_after_warmup(h):
    h.r.apply({"action": "mine", "job": JOB})
    h.t += runner.WARMUP_SECONDS                         # DAG-Aufbau: noch keine Hashrate, kein Neustart
    h.r.tick(None)
    assert len(h.spawned) == 1
    h.t += runner.STALL_SECONDS + 1
    h.r.tick(None)
    assert len(h.spawned) == 2


def test_hashrate_keeps_watchdog_quiet(h):
    h.r.apply({"action": "mine", "job": JOB})
    h.api = {"hashrate": 2e7, "accepted": 3, "rejected": 0, "watts": None}
    for _ in range(20):
        h.t += 60
        st = h.r.tick(150.0)
    assert len(h.spawned) == 1 and st["hashrate"] == 2e7 and st["miner"] == "mine"


def test_benchmark_reports_median_after_warmup_once(h):
    h.r.apply({"action": "benchmark", "seconds": 180, "job": JOB})
    rates = [1e6, 9e9, 2e7, 2.1e7, 2.2e7, 2.0e7, 1.9e7, 2.05e7]   # Ausreißer in der Aufwärmphase
    result = None
    for hr in rates:
        h.t += 25
        h.api = {"hashrate": hr, "accepted": 0, "rejected": 0, "watts": None}
        st = h.r.tick(170.0)
        result = st.get("benchmark_result") or result
    assert result and result["coin"] == "rvn" and result["miner"] == "rigel"
    assert 1.9e7 <= result["hashrate"] <= 2.2e7 and result["watts"] == 170.0
    assert h.r.proc is None and "benchmark_result" not in h.r.tick(None)   # nur einmal gemeldet


def test_benchmark_without_hashrate_reports_error(h):
    h.r.apply({"action": "benchmark", "seconds": 60, "job": JOB})
    h.t += 61
    st = h.r.tick(None)
    assert st["benchmark_result"]["hashrate"] is None and st["benchmark_result"]["error"] == "no_hashrate"


def test_fetch_failure_in_benchmark_is_reported(h, monkeypatch):
    def boom(name, d):
        raise fetch.FetchError("sha256_mismatch:abc")
    h.r._ensure = boom
    h.r.apply({"action": "benchmark", "seconds": 60, "job": JOB})
    st = h.r.tick(None)
    assert st["benchmark_result"]["error"].startswith("fetch:")


def test_watchdog_respects_warmup_even_if_stall_window_shorter(h, monkeypatch):
    monkeypatch.setattr(runner, "STALL_SECONDS", 10)
    h.r.apply({"action": "mine", "job": JOB})
    h.t += runner.WARMUP_SECONDS - 1                     # DAG-Aufbau läuft noch
    h.r.tick(None)
    assert len(h.spawned) == 1


def test_benchmark_ignores_warmup_samples(h):
    h.r.apply({"action": "benchmark", "seconds": 90, "job": JOB})
    h.api = {"hashrate": 9e9, "accepted": 0, "rejected": 0, "watts": None}   # Ausreißer beim Anlaufen
    for _ in range(2):                    # zwei Proben: ohne Filter landet eine in der „zweiten Hälfte“
        h.t += 20
        h.r.tick(None)
    h.t += 51
    h.api = {"hashrate": 2e7, "accepted": 0, "rejected": 0, "watts": None}
    st = h.r.tick(None)
    assert st["benchmark_result"]["hashrate"] == 2e7
