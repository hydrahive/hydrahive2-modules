"""Grafikkarten erkennen und Messwerte lesen — ohne Abhängigkeiten.

NVIDIA: ``nvidia-smi --query-gpu=… --format=csv,noheader,nounits`` (eine Zeile je Karte)
AMD:    sysfs des amdgpu-Treibers (/sys/class/drm/card*/device):
        vendor 0x1002, mem_info_vram_total (Bytes), hwmon/temp*_input (m°C),
        hwmon/power1_average bzw. power1_input (µW), gpu_busy_percent (%).

Alle Karten werden gemeldet (``gpus``); dazu eine Zusammenfassung für Anzeige und
Energie-Steuerung: Watt summiert, Temperatur der heißesten Karte. Die Miner nutzen
ohne Geräte-Auswahl ohnehin alle Karten, die Hashrate ist schon die Summe.

AMD ab Linux 6.15: Temperatur/Watt/Last liefern im Laufzeit-Ruhezustand nur EPERM
(amdgpu_pm_get_access_if_active) — die Karte wird fürs Auslesen nicht mehr geweckt.
Dann ``sensors: asleep`` statt stiller Lücken.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from . import amdinfo

NVIDIA_FIELDS = "name,memory.total,driver_version,temperature.gpu,power.draw,fan.speed,utilization.gpu,pci.bus_id"
AMD_VENDOR = "0x1002"
_CARD_RE = re.compile(r"^card(\d+)$")


def _num(v: str | None) -> float | None:
    try:
        return float(v.strip())  # type: ignore[union-attr]
    except (ValueError, AttributeError):
        return None  # "[N/A]", "[Not Supported]", None …


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
            "pci": parts[7] if len(parts) > 7 else None, "sensors": "ok",
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


class _Reader:
    """Liest sysfs-Werte und merkt sich, ob der Treiber Lesen verweigert hat (EPERM)."""

    def __init__(self) -> None:
        self.denied = False

    def text(self, p: Path | None) -> str | None:
        if p is None:
            return None
        try:
            return p.read_text().strip()
        except PermissionError:
            self.denied = True
            return None
        except OSError:
            return None

    def first(self, paths: list[Path], div: float) -> float | None:
        """Erster lesbare Wert > 0 aus mehreren Kandidaten (z. B. average, sonst input)."""
        for p in paths:
            v = _num(self.text(p)) if p.exists() else None
            if v is not None and v > 0:
                return round(v / div, 1)
        return None


def _pci_slot(rd: _Reader, dev: Path) -> str | None:
    for line in (rd.text(dev / "uevent") or "").splitlines():
        if line.startswith("PCI_SLOT_NAME="):
            return line.split("=", 1)[1]
    return None


def _amd_model(rd: _Reader, dev: Path) -> str:
    """product_name (nur Profi-Karten) → Name aus amdgpu.ids → „AMD 0x67df“."""
    device = rd.text(dev / "device")
    return rd.text(dev / "product_name") or amdinfo.name(device, rd.text(dev / "revision")) or f"AMD {device}"


def _fan_pct(rd: _Reader, hw: Path | None) -> float | None:
    """Lüfter in % aus hwmon pwm1 (0…pwm1_max, Standard 255)."""
    if hw is None:
        return None
    pwm, top = _num(rd.text(hw / "pwm1")), _num(rd.text(hw / "pwm1_max"))
    top = 255.0 if top is None else top          # fehlt pwm1_max → Kernel-Standard 255
    if pwm is None or pwm < 0 or top <= 0:
        return None
    return round(min(pwm / top, 1.0) * 100, 1)


def read_amd(drm_root: Path = Path("/sys/class/drm")) -> list[dict]:
    cards = sorted((int(m.group(1)), p) for p in drm_root.glob("card*") if (m := _CARD_RE.match(p.name)))
    gpus = []
    for _, card in cards:
        dev = card / "device"
        rd = _Reader()
        if rd.text(dev / "vendor") != AMD_VENDOR:
            continue
        hw = next(iter(sorted(dev.glob("hwmon/hwmon*"))), None)
        temp = power = None
        if hw is not None:
            temp = rd.first([hw / f"temp{i}_input" for i in (1, 2, 3)], 1000)        # edge, hotspot, mem
            power = rd.first([hw / "power1_average", hw / "power1_input"], 1_000_000)
        fan = _fan_pct(rd, hw)
        util = _num(rd.text(dev / "gpu_busy_percent"))
        vram = _num(rd.text(dev / "mem_info_vram_total"))
        asleep = rd.denied or rd.text(dev / "power" / "runtime_status") == "suspended"
        sensors = "no_hwmon" if hw is None else ("asleep" if asleep and temp is None and power is None else "ok")
        gpus.append({
            "gpu_vendor": "amd", "gpu_model": _amd_model(rd, dev),
            "gpu_mem_mb": int(vram / 1048576) if vram else None,
            "driver": rd.text(dev / "driver/module/version") or "amdgpu",
            "temp_c": temp, "power_w": power, "fan_pct": fan, "util_pct": util,
            "pci": _pci_slot(rd, dev), "sensors": sensors,
        })
    return gpus


def _model_summary(gpus: list[dict]) -> str:
    if len(gpus) == 1:
        return gpus[0].get("gpu_model") or "—"
    vendor = {"amd": "AMD", "nvidia": "NVIDIA"}.get(gpus[0].get("gpu_vendor") or "", "GPU")
    parts = ", ".join(f"{n}× {m}" for m, n in Counter(g.get("gpu_model") or "?" for g in gpus).most_common())
    return f"{len(gpus)}× {vendor} ({parts})"


def summarize(gpus: list[dict]) -> dict:
    """Ein Rig-Eintrag aus allen Karten: Watt-Summe, heißeste Karte, mittlere Last, kleinster Speicher."""
    if not gpus:
        return {"gpu_vendor": "none", "gpu_count": 0, "gpus": []}

    def known(k):
        return [g[k] for g in gpus if isinstance(g.get(k), (int, float))]

    power, temps, utils, mems = known("power_w"), known("temp_c"), known("util_pct"), known("gpu_mem_mb")
    fans = known("fan_pct")
    first = gpus[0]
    return {
        "gpu_vendor": first.get("gpu_vendor"), "gpu_model": _model_summary(gpus),
        "gpu_mem_mb": min(mems) if mems else None, "driver": first.get("driver"),
        "temp_c": max(temps) if temps else None, "power_w": round(sum(power), 1) if power else None,
        "util_pct": round(sum(utils) / len(utils), 1) if utils else None,
        "fan_pct": max(fans) if fans else None,
        "gpu_count": len(gpus), "gpus": gpus,
    }


VENDORS = ("nvidia", "amd")


def amd_opencl(dirs: list[Path] | None = None) -> str:
    return amdinfo.opencl(dirs)


def detect() -> dict:
    """Alle Karten beider Hersteller + Zusammenfassung; ``groups`` je Hersteller.

    Gemischter Rechner → ``gpu_vendor = "mixed"``; jede Gruppe bekommt eigenen Miner.
    """
    by_vendor = {"nvidia": _nvidia(), "amd": read_amd()}
    groups = {v: summarize(cards) for v, cards in by_vendor.items() if cards}
    if "amd" in groups:
        groups["amd"]["opencl"] = amd_opencl()
    out = summarize(by_vendor["nvidia"] + by_vendor["amd"])
    if len(groups) > 1:
        out["gpu_vendor"] = "mixed"
        out["gpu_model"] = " + ".join(g["gpu_model"] for g in groups.values())
    out["groups"] = groups
    return out
