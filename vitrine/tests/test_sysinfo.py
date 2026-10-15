"""Systemstatus aus /proc und hwmon — mit Fake-Verzeichnissen, kein Zugriff aufs echte System nötig."""
from __future__ import annotations

from renderer import sysinfo


def _hwmon(tmp_path, name, temp=None):
    d = tmp_path / "hwmon" / f"hwmon{len(list((tmp_path / 'hwmon').glob('*'))) if (tmp_path / 'hwmon').exists() else 0}"
    d.mkdir(parents=True)
    (d / "name").write_text(name + "\n")
    if temp is not None:
        (d / "temp1_input").write_text(f"{temp}\n")
    return tmp_path / "hwmon"


def test_ram_prozent(tmp_path):
    m = tmp_path / "meminfo"
    m.write_text("MemTotal:       64000000 kB\nMemFree:  1 kB\nMemAvailable:   48000000 kB\n")
    assert sysinfo.ram_percent(m) == 25


def test_ram_ohne_datei(tmp_path):
    assert sysinfo.ram_percent(tmp_path / "fehlt") is None


def test_gpu_temperatur_amdgpu(tmp_path):
    _hwmon(tmp_path, "k10temp", 61000)
    root = _hwmon(tmp_path, "amdgpu", 47500)
    assert sysinfo.gpu_temp(root) == 47


def test_gpu_ohne_sensor(tmp_path):
    root = _hwmon(tmp_path, "amdgpu")
    assert sysinfo.gpu_temp(root) is None
    assert sysinfo.gpu_temp(tmp_path / "nichts") is None


def test_statuszeile():
    s = sysinfo.status_line(hydra="active", load=0.43, ram=25, gpu=47)
    assert s == "Hydra läuft  ·  Last 0.4  ·  RAM 25%  ·  GPU 47°C"
    assert sysinfo.status_line(hydra="activating", load=1.0, ram=None, gpu=None) == "Hydra startet  ·  Last 1.0"
    assert sysinfo.status_line(hydra="failed", load=0.0, ram=3, gpu=None).startswith("Hydra Fehler")
    assert sysinfo.status_line(hydra="inactive", load=0.0, ram=3, gpu=None).startswith("Hydra aus")
