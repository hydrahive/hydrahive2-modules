"""Systemstatus für die Leiste: Hydra-Dienst, Last, RAM, GPU-Temperatur. Alles optional — fehlt etwas, entfällt es."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

_HYDRA = {"active": "läuft", "activating": "startet", "reloading": "startet", "deactivating": "stoppt",
          "failed": "Fehler", "inactive": "aus"}


def ram_percent(meminfo: Path = Path("/proc/meminfo")) -> int | None:
    try:
        vals = {line.split(":")[0]: int(line.split()[1]) for line in meminfo.read_text().splitlines() if ":" in line}
        return round(100 - 100 * vals["MemAvailable"] / vals["MemTotal"])
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return None


def gpu_temp(hwmon: Path = Path("/sys/class/hwmon")) -> int | None:
    try:
        dirs = sorted(hwmon.iterdir())
    except OSError:
        return None
    for d in dirs:
        try:
            if (d / "name").read_text().strip() == "amdgpu":
                return int((d / "temp1_input").read_text()) // 1000
        except (OSError, ValueError):
            continue
    return None


def hydra_state(unit: str = "hydrahive2") -> str:
    try:
        return subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=3).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unbekannt"


def status_line(*, hydra: str, load: float, ram: int | None, gpu: int | None) -> str:
    parts = [f"Hydra {_HYDRA.get(hydra, hydra)}", f"Last {load:.1f}"]
    if ram is not None:
        parts.append(f"RAM {ram}%")
    if gpu is not None:
        parts.append(f"GPU {gpu}°C")
    return "  ·  ".join(parts)


def current() -> str:
    return status_line(hydra=hydra_state(), load=os.getloadavg()[0], ram=ram_percent(), gpu=gpu_temp())
