"""AMD ohne OpenCL-Treiber: klar melden statt 22 Messungen scheitern zu lassen.

Kugelfang, 04.10.2026: amdgpu erkennt alle Karten, aber kein OpenCL-Anbieter
(/etc/OpenCL/vendors leer) → „OpenCL not found“, Watchdog-Kette ohne Hash.
Client prüft die ICD-Dateien und meldet ``opencl: "missing"``; Server stoppt die
AMD-Gruppe mit Grund ``amd_opencl_missing`` und speichert keine Fehlschläge.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RIG_DIR = Path(__file__).resolve().parents[1] / "rig"
if str(RIG_DIR) not in sys.path:
    sys.path.insert(0, str(RIG_DIR))

from backend import catalog, runtime_store, store
from backend.profit import CoinQuote
from hydrahive_rig import agent, gpu
from tests.test_planner import D, _rig


# ---- Client: Prüfung ----
@pytest.mark.parametrize("files, expected", [
    ({}, "missing"),                                                   # Ordner leer (Kugelfang)
    ({"rusticl.icd": "libRusticlOpenCL.so.1"}, "ok"),
    ({"amdocl64.icd": "libamdocl64.so"}, "ok"),                         # ROCm / amdgpu-pro
    ({"nvidia.icd": "libnvidia-opencl.so.1"}, "missing"),               # nur NVIDIA hilft AMD nicht
    ({"pocl.icd": "libpocl.so.2"}, "missing"),                          # nur CPU
    ({"leer.icd": ""}, "missing"),
])
def test_amd_opencl_detection(tmp_path, files, expected):
    for name, content in files.items():
        (tmp_path / name).write_text(content + "\n")
    assert gpu.amd_opencl([tmp_path]) == expected


def test_amd_opencl_missing_dir(tmp_path):
    assert gpu.amd_opencl([tmp_path / "gibt-es-nicht"]) == "missing"


def test_amd_opencl_second_dir(tmp_path):
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "rusticl.icd").write_text("libRusticlOpenCL.so.1\n")
    assert gpu.amd_opencl([tmp_path / "a", tmp_path / "b"]) == "ok"


def test_amd_group_reports_opencl(monkeypatch):
    amd = {"gpu_vendor": "amd", "gpu_model": "RX 470", "gpu_mem_mb": 8192, "temp_c": 50.0, "power_w": 90.0,
           "fan_pct": 30.0, "util_pct": 0.0, "pci": "0000:01:00.0", "sensors": "ok"}
    monkeypatch.setattr(gpu, "_nvidia", list)
    monkeypatch.setattr(gpu, "read_amd", lambda: [amd])
    monkeypatch.setattr(gpu, "amd_opencl", lambda dirs=None: "missing")
    card = gpu.detect()
    assert card["groups"]["amd"]["opencl"] == "missing"
    st = agent.group_states(card, {})
    assert st["amd"]["opencl"] == "missing"


def test_nvidia_group_has_no_opencl_field(monkeypatch):
    nv = {"gpu_vendor": "nvidia", "gpu_model": "RTX", "gpu_mem_mb": 8192, "temp_c": 50.0, "power_w": 90.0,
          "fan_pct": 30.0, "util_pct": 0.0, "pci": "0000:01:00.0", "sensors": "ok"}
    monkeypatch.setattr(gpu, "_nvidia", lambda: [nv])
    monkeypatch.setattr(gpu, "read_amd", list)
    assert "opencl" not in gpu.detect()["groups"]["nvidia"]


# ---- Server ----
@pytest.fixture
def quotes():
    store.replace_quotes([CoinQuote(coin=c, name=c, algo="A", fee=0.01, fee_type="PPS+",
                                    profit_per_hs_day=1e-6, price_usd=1.0) for c in catalog.coins()])


def _amd_report(client, e, opencl):
    info = {"gpu_vendor": "amd", "gpu_model": "RX 470", "gpu_mem_mb": 8192, "client_version": "0.4.2"}
    state = {"miner": "idle", "groups": {"amd": {"gpu_count": 3, "gpu_mem_mb": 8192, **({"opencl": opencl}
                                                                                           if opencl else {})}}}
    r = client.post(f"{D}/report", headers={"Authorization": f"Bearer {e['token']}"},
                    json={"info": info, "state": state})
    assert r.status_code == 200, r.text
    return r.json()["desired"]


def test_server_stops_amd_group_without_opencl(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    d = _amd_report(client, e, "missing")
    assert d["action"] == "stop" and d["reason"] == "amd_opencl_missing"
    assert runtime_store.bench_for(e["rig_id"]) == ({}, set())


def test_server_benchmarks_once_opencl_installed(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    _amd_report(client, e, "missing")
    d = _amd_report(client, e, "ok")
    assert d["action"] == "benchmark"


def test_old_client_without_field_is_not_blocked(client, admin_headers, quotes):
    store.update_config({"kryptex_user": "krxTEST"})
    e = _rig(client, admin_headers)
    assert _amd_report(client, e, None)["action"] == "benchmark"
