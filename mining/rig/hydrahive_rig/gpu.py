"""Grafikkarte erkennen und Messwerte lesen — ohne Abhängigkeiten.

NVIDIA: ``nvidia-smi --query-gpu=… --format=csv,noheader,nounits``
AMD:    sysfs des amdgpu-Treibers (/sys/class/drm/card*/device):
        vendor 0x1002, mem_info_vram_total (Bytes), hwmon/temp1_input (m°C),
        hwmon/power1_average bzw. power1_input (µW), gpu_busy_percent (%).
V1: genau eine Karte pro Rig (Spec). Mehrere → erste, mit Hinweis.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

NVIDIA_FIELDS = "name,memory.total,driver_version,temperature.gpu,power.draw,fan.speed,utilization.gpu"
AMD_VENDOR = "0x1002"
NVIDIA_VENDOR = "0x10de"


def _num(v: str) -> float | None:
    try:
        return float(v.strip())
    except (ValueError, AttributeError):
        return None  # "[N/A]", "[Not Supported]" …


def parse_nvidia_smi(out: str) -> list[dict]:
    gpus = []
    for line in (out or "").strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        mem = _num(parts[1])
        gpus.append({
            "gpu_vendor": "nvidia", "gpu_model": parts[0], "gpu_mem_mb": int(mem) if mem else None,
            "driver": parts[2], "temp_c": _num(parts[3]), "power_w": _num(parts[4]),
            "fan_pct": _num(parts[5]), "util_pct": _num(parts[6]),
        })
    return gpus


def _nvidia() -> list[dict]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        r = subprocess.run([exe, f"--query-gpu={NVIDIA_FIELDS}", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_nvidia_smi(r.stdout) if r.returncode == 0 else []


def _read(p: Path) -> str | None:
    try:
        return p.read_text().strip()
    except OSError:
        return None


def _scaled(p: Path | None, div: float) -> float | None:
    if p is None:
        return None
    v = _num(_read(p) or "")
    return round(v / div, 1) if v is not None else None


def read_amd(drm_root: Path = Path("/sys/class/drm")) -> list[dict]:
    gpus = []
    for dev in sorted(drm_root.glob("card[0-9]*/device")):
        if "-" in dev.parent.name or _read(dev / "vendor") != AMD_VENDOR:
            continue
        hw = next(iter(sorted(dev.glob("hwmon/hwmon*"))), None)
        power = None
        if hw is not None:
            power = next((hw / f for f in ("power1_average", "power1_input") if (hw / f).exists()), None)
        vram = _num(_read(dev / "mem_info_vram_total") or "")
        gpus.append({
            "gpu_vendor": "amd", "gpu_model": _read(dev / "product_name") or f"AMD {_read(dev / 'device')}",
            "gpu_mem_mb": int(vram / 1048576) if vram else None,
            "driver": _read(dev / "driver/module/version") or "amdgpu",
            "temp_c": _scaled(hw / "temp1_input" if hw else None, 1000),
            "power_w": _scaled(power, 1_000_000),
            "fan_pct": None, "util_pct": _num(_read(dev / "gpu_busy_percent") or ""),
        })
    return gpus


def detect() -> dict:
    """Erste gefundene Karte (NVIDIA vor AMD) oder ``gpu_vendor: none``."""
    gpus = _nvidia() or read_amd()
    if not gpus:
        return {"gpu_vendor": "none", "gpu_count": 0}
    return {**gpus[0], "gpu_count": len(gpus)}
