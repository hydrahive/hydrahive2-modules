"""Hersteller-Gruppen im Client: gemischter Rechner (AMD + NVIDIA) → je Hersteller eigener Miner.

Rechner mit nur einem Hersteller verhalten sich wie bisher (keine Geräteauswahl, Worker = Rechnername).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from hydrahive_rig import agent, catalog, gpu, runner

JOB = {"coin": "erg", "miner": "lolminer", "algo": "AUTOLYKOS2", "user": "krxXJK8JJW", "worker": "rig-01",
       "region": "eu"}
NV = {"gpu_vendor": "nvidia", "gpu_model": "RTX 3070", "gpu_mem_mb": 8192, "temp_c": 60.0, "power_w": 150.0,
      "util_pct": 99.0, "fan_pct": 40.0, "pci": "0000:01:00.0", "sensors": "ok"}
AMD = {"gpu_vendor": "amd", "gpu_model": "RX 6800", "gpu_mem_mb": 16384, "temp_c": 70.0, "power_w": 200.0,
       "util_pct": 98.0, "fan_pct": None, "pci": "0000:03:00.0", "sensors": "ok"}


# ---- Erkennung ----
def test_detect_reports_both_vendors(monkeypatch):
    monkeypatch.setattr(gpu, "_nvidia", lambda: [NV])
    monkeypatch.setattr(gpu, "read_amd", lambda: [AMD, {**AMD, "pci": "0000:04:00.0"}])
    d = gpu.detect()
    assert d["gpu_count"] == 3 and d["gpu_vendor"] == "mixed"
    assert set(d["groups"]) == {"nvidia", "amd"}
    assert d["groups"]["amd"]["gpu_count"] == 2 and d["groups"]["amd"]["power_w"] == 400.0
    assert d["groups"]["nvidia"]["gpu_mem_mb"] == 8192
    assert d["power_w"] == 550.0 and d["temp_c"] == 70.0


def test_detect_single_vendor_unchanged(monkeypatch):
    monkeypatch.setattr(gpu, "_nvidia", lambda: [NV])
    monkeypatch.setattr(gpu, "read_amd", list)
    d = gpu.detect()
    assert d["gpu_vendor"] == "nvidia" and list(d["groups"]) == ["nvidia"]
    assert d["gpu_model"] == "RTX 3070"


def test_detect_nothing(monkeypatch):
    monkeypatch.setattr(gpu, "_nvidia", list)
    monkeypatch.setattr(gpu, "read_amd", list)
    assert gpu.detect() == {"gpu_vendor": "none", "gpu_count": 0, "gpus": [], "groups": {}}


# ---- Startbefehl mit Herstellerfilter ----
@pytest.mark.parametrize("miner, algo, vendor, flag", [
    ("lolminer", "AUTOLYKOS2", "amd", ["--devices", "AMD"]),
    ("lolminer", "AUTOLYKOS2", "nvidia", ["--devices", "NVIDIA"]),
    ("srbminer", "autolykos2", "amd", ["--disable-gpu-nvidia", "--disable-gpu-intel"]),
    ("srbminer", "autolykos2", "nvidia", ["--disable-gpu-amd", "--disable-gpu-intel"]),
])
def test_mixed_rig_filters_devices(miner, algo, vendor, flag):
    spec = catalog.build({**JOB, "miner": miner, "algo": algo}, vendor, mixed=True)
    assert all(f in spec["args"] for f in flag)


def test_single_vendor_rig_has_no_device_filter():
    spec = catalog.build(JOB, "amd")
    assert "--devices" not in spec["args"]


def test_rigel_needs_no_filter_even_when_mixed():
    spec = catalog.build({**JOB, "miner": "rigel", "algo": "autolykos2"}, "nvidia", mixed=True)
    assert "--devices" not in spec["args"] and "-d" not in spec["args"]


def test_groups_use_separate_api_ports():
    a = catalog.build(JOB, "amd", mixed=True, group="amd")
    n = catalog.build({**JOB, "miner": "rigel", "algo": "autolykos2"}, "nvidia", mixed=True, group="nvidia")
    assert a["api_port"] != n["api_port"]
    assert str(a["api_port"]) in a["args"] and str(n["api_port"]) in " ".join(n["args"])


def test_mixed_rig_worker_names_per_vendor():
    """Kryptex soll beide Gruppen getrennt zählen: rig-01-amd / rig-01-nvidia."""
    a = catalog.build(JOB, "amd", mixed=True, group="amd")
    assert "krxXJK8JJW/rig-01-amd" in a["args"]
    single = catalog.build(JOB, "amd")
    assert "krxXJK8JJW/rig-01" in single["args"]


def test_amd_job_cannot_run_rigel_even_in_mixed_rig():
    with pytest.raises(catalog.JobError):
        catalog.build({**JOB, "miner": "rigel", "algo": "autolykos2"}, "amd", mixed=True)


# ---- Agent: je Gruppe ein Runner, Soll je Gruppe ----
class FakeRunner:
    def __init__(self, vendor):
        self.vendor, self.applied, self.proc = vendor, [], None

    def apply(self, desired):
        self.applied.append(desired)

    def tick(self, watts):
        return {"miner": "idle", "hashrate": None, "watts_seen": watts}


def test_agent_routes_desired_to_each_group():
    runners = {"nvidia": FakeRunner("nvidia"), "amd": FakeRunner("amd")}
    desired = {"action": "stop", "groups": {"nvidia": {"action": "mine", "job": {"coin": "qtc"}},
                                            "amd": {"action": "benchmark", "job": {"coin": "erg"}}}}
    agent.apply_desired(runners, desired)
    assert runners["nvidia"].applied[-1]["job"]["coin"] == "qtc"
    assert runners["amd"].applied[-1]["action"] == "benchmark"


def test_agent_old_server_flat_desired_goes_to_single_group():
    """Alter Server kennt keine Gruppen → flaches Soll gilt für die (einzige) Gruppe."""
    runners = {"nvidia": FakeRunner("nvidia")}
    agent.apply_desired(runners, {"action": "mine", "job": {"coin": "cfx"}})
    assert runners["nvidia"].applied[-1]["job"]["coin"] == "cfx"


def test_agent_old_server_mixed_rig_stops_both():
    """Alter Server, gemischter Rechner: flaches Soll wäre für eine Gruppe falsch → beide aus."""
    runners = {"nvidia": FakeRunner("nvidia"), "amd": FakeRunner("amd")}
    agent.apply_desired(runners, {"action": "mine", "job": {"coin": "cfx", "miner": "rigel"}})
    assert runners["nvidia"].applied[-1] == {"action": "stop"} and runners["amd"].applied[-1] == {"action": "stop"}


def test_agent_missing_group_in_desired_stops_that_group():
    runners = {"nvidia": FakeRunner("nvidia"), "amd": FakeRunner("amd")}
    agent.apply_desired(runners, {"action": "stop", "groups": {"nvidia": {"action": "mine", "job": {}}}})
    assert runners["amd"].applied[-1]["action"] == "stop"


def test_group_state_contains_per_group_runner_state():
    card = {**gpu.summarize([NV, AMD]), "groups": {"nvidia": gpu.summarize([NV]), "amd": gpu.summarize([AMD])}}
    runners = {"nvidia": FakeRunner("nvidia"), "amd": FakeRunner("amd")}
    st = agent.group_states(card, runners)
    assert set(st) == {"nvidia", "amd"}
    assert st["amd"]["watts_seen"] == 200.0 and st["nvidia"]["gpu_count"] == 1


def test_runner_reads_its_own_api_port(tmp_path, monkeypatch):
    ports = []
    r = runner.Runner(tmp_path, "amd", group="amd", mixed=True, spawn=lambda *a, **k: type("P", (), {
        "pid": 1, "poll": lambda s: None, "wait": lambda s, timeout=None: 0})(),
        ensure=lambda n, d: tmp_path / n, read_api=lambda kind, port: ports.append(port) or None)
    monkeypatch.setattr(runner.os, "killpg", lambda *a: None)
    r.apply({"action": "mine", "job": JOB})
    r.tick(None)
    assert ports == [catalog.api_port("amd")]


# ---- CUDA verstecken: SRBMiner 3.7.1 ignoriert --disable-gpu-nvidia (auf wks197 gemessen) ----
@pytest.mark.parametrize("miner, algo", [("srbminer", "autolykos2"), ("lolminer", "AUTOLYKOS2")])
def test_mixed_amd_group_hides_cuda(miner, algo):
    spec = catalog.build({**JOB, "miner": miner, "algo": algo}, "amd", mixed=True, group="amd")
    assert spec["env"] == {"CUDA_VISIBLE_DEVICES": "", "RUSTICL_ENABLE": "radeonsi"}


def test_nvidia_group_and_single_vendor_keep_cuda():
    nv = catalog.build({**JOB, "miner": "srbminer", "algo": "autolykos2"}, "nvidia", mixed=True, group="nvidia")
    amd_only = catalog.build(JOB, "amd")
    assert nv.get("env", {}) == {} and "CUDA_VISIBLE_DEVICES" not in amd_only["env"]


def test_runner_passes_env_to_miner(tmp_path, monkeypatch):
    seen = {}

    def spawn(args, **kw):
        seen.update(kw.get("env") or {})
        return type("P", (), {"pid": 1, "poll": lambda s: None, "wait": lambda s, timeout=None: 0})()

    monkeypatch.setenv("HH_PROBE", "bleibt")
    r = runner.Runner(tmp_path, "amd", group="amd", mixed=True, spawn=spawn, ensure=lambda n, d: tmp_path / n,
                      read_api=lambda kind, port: None)
    monkeypatch.setattr(runner.os, "killpg", lambda *a: None)
    r.apply({"action": "mine", "job": JOB})
    assert seen.get("CUDA_VISIBLE_DEVICES") == "" and seen.get("HH_PROBE") == "bleibt"
