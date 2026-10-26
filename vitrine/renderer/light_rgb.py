"""S8 Licht: OpenRGB aufrufen (SPEC-LICHT.md). Nur feste Argumente und geprüfte Werte, nie eine Shell.

Gemessen am 26.10.2026 auf .2: ein Aufruf dauert ~1,2 s (Gerätesuche bei jedem Start); OpenRGB meldet manche Fehler mit
Rückgabewert 0 (z. B. „Error: Mode … not available“) → die Ausgabe wird mit ausgewertet. Ohne Recht auf /dev/hidraw*
findet `-l` nichts (leere Liste, kein Fehler).
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import light_config

TIMEOUT = 30.0
_MODES = {"static": "static", "breathing": "breathing", "flashing": "flashing"}
_DEV = re.compile(r"^(\d+): (.+)$")


class LightError(RuntimeError):
    pass


@dataclass(frozen=True)
class Device:
    index: int
    name: str


def _env(cfg_dir: Path) -> dict:
    # Eigener Ordner statt $HOME: der Vitrine-Dienst hat ProtectHome=read-only
    return {**os.environ, "HOME": str(cfg_dir), "XDG_CONFIG_HOME": str(cfg_dir)}


def _base(binary: str, cfg_dir: Path) -> list[str]:
    return [binary, "--noautoconnect", "--config", str(cfg_dir)]


def find(cfg_dir: Path, *, binary: str = "openrgb", run=subprocess.run, timeout: float = TIMEOUT) -> Device | None:
    """Erstes Gerät vom Typ Motherboard aus `openrgb -l`; None, wenn keins da (oder OpenRGB fehlt)."""
    cfg_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = run([*_base(binary, cfg_dir), "-l"], capture_output=True, text=True, timeout=timeout, env=_env(cfg_dir))
    except (OSError, subprocess.SubprocessError):
        return None
    current: Device | None = None
    for line in (r.stdout or "").splitlines():
        m = _DEV.match(line)
        if m:
            current = Device(int(m.group(1)), m.group(2).strip())
        elif current and line.strip().startswith("Type:") and line.split(":", 1)[1].strip() == "Motherboard":
            return current
    return None


def command(look, device: Device, cfg_dir: Path, *, binary: str = "openrgb") -> list[str]:
    """Befehlszeile für einen Zustand. Ungültige Werte → LightError (es geht nichts an OpenRGB)."""
    effect, color = look.effect, look.color
    if effect not in light_config.EFFECTS or light_config.color(color) != color:
        raise LightError(f"ungültiger Zustand: {effect!r} {color!r}")
    for v in (look.brightness, look.speed):
        if type(v) is not int or not 0 <= v <= 100:
            raise LightError(f"ungültiger Wert: {v!r}")
    args = [*_base(binary, cfg_dir), "-d", str(int(device.index))]
    if effect == "off":
        return [*args, "-m", "static", "-c", "000000", "-b", "0"]
    args += ["-m", _MODES[effect], "-c", color, "-b", str(look.brightness)]
    if effect in ("breathing", "flashing"):
        args += ["-s", str(look.speed)]
    return args


def apply(look, device: Device, cfg_dir: Path, *, binary: str = "openrgb", run=subprocess.run,
          timeout: float = TIMEOUT) -> None:
    args = command(look, device, cfg_dir, binary=binary)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = run(args, capture_output=True, text=True, timeout=timeout, env=_env(cfg_dir))
    except subprocess.TimeoutExpired:
        raise LightError("OpenRGB: Zeitüberschreitung") from None
    except OSError as e:
        raise LightError(f"OpenRGB nicht startbar: {e}") from None
    out = f"{r.stdout or ''}\n{r.stderr or ''}"
    err = next((ln.strip() for ln in out.splitlines() if ln.strip().startswith("Error")), "")
    if r.returncode != 0 or err:
        raise LightError(err or f"OpenRGB: Rückgabewert {r.returncode}")
