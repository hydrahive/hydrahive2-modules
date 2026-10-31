"""Lautheit je Titel (0.2.3): einmal messen, speichern, beim Abspielen als fester Wert an Liquidsoap mitgeben.

Vorher regelte der Sender mit normalize() laufend nach. Das zog am Titelende das Ausklingen hoch – der alte Titel wurde
vor der Überblendung lauter (Befund Till 31.10., gemessen mit echter Musik: −45 dB → −29 dB). Ein fester Wert je Titel
lässt das Ausklingen so, wie es aufgenommen ist, und gleicht trotzdem laute und leise Titel an.

Gemessen wird mit ffmpeg (ebur128, integrierte Lautheit in LUFS) beim ersten Abspielen – ~0,1 s je Titel, während der
vorige noch läuft. ffmpeg ist auf jedem HydraHive-Server (Kern-Installer, 00-deps.sh).
"""
from __future__ import annotations

import re
import shutil
import subprocess

TARGET_LUFS = -14.0          # üblicher Wert für Streaming-Dienste
MAX_GAIN_DB = 10.0           # sehr leise Titel nicht unbegrenzt hochziehen (Rauschen, Übersteuern)
MIN_GAIN_DB = -15.0
TIMEOUT_S = 60
_SILENT = -60.0              # darunter: Stille/unbrauchbar → nicht angleichen
_I = re.compile(r"Integrated loudness:\s*\n\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS")


def gain_for(lufs: float) -> float | None:
    """Verstärkung in dB für den Titel, gerundet, begrenzt. None = nicht angleichen."""
    if lufs <= _SILENT:
        return None
    return round(min(MAX_GAIN_DB, max(MIN_GAIN_DB, TARGET_LUFS - lufs)), 1)


def parse_lufs(text: str) -> float | None:
    m = _I.search(text or "")
    return float(m.group(1)) if m else None


def measure(fh, fmt: str) -> float | None:
    """Integrierte Lautheit der Datei (Datei-Objekt zum Lesen). None, wenn nicht messbar."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        data = fh.read()
        r = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-f", fmt if fmt != "m4a" else "mov", "-i", "pipe:0",
                            "-vn", "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                           input=data, capture_output=True, timeout=TIMEOUT_S, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return parse_lufs(r.stderr.decode("utf-8", "replace") if isinstance(r.stderr, bytes) else r.stderr)
