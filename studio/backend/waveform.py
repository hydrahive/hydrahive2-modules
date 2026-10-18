"""Wellenform eines Tonclips (Spec „Bauplan Etappe 5“, 5a): ffmpeg dekodiert einmal zu mono PCM, daraus 50 Spitzenwerte
je Sekunde (0–100). Ergebnis im wegwerfbaren Cache studio/cache/peaks/, Schlüssel = Pfad + Größe + Änderungszeit.
Idee wie videoeditor/backend/_audio_peaks.py, eigene Fassung (Module importieren nicht übereinander).

Ist die Datei nicht lesbar, kommt eine leere Liste (flache Linie) zurück und nichts wird abgelegt.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
from array import array

from ._sources import AUDIO_EXT, VIDEO_EXT
from ._store import project_root, read_json, root, safe_rel, write_json

logger = logging.getLogger("hhmod_studio.waveform")

PER_SECOND = 50
RATE = 8000                       # reicht für die Hüllkurve, hält die Datenmenge klein
MAX_SECONDS = 4 * 3600
TIMEOUT = 120


class NotFound(LookupError):
    """Kein Ton oder Video im Projekt unter diesem Pfad."""


def peaks_from_pcm(pcm: bytes) -> list[int]:
    """Mono s16le → Spitzenwert je 1/PER_SECOND s, 0–100. Rein, ohne ffmpeg."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    step = RATE // PER_SECOND
    return [round(max(abs(x) for x in samples[i:i + step]) * 100 / 32768) for i in range(0, len(samples), step)]


def _decode(path) -> bytes | None:
    if not shutil.which("ffmpeg"):
        return None
    try:
        out = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-t", str(MAX_SECONDS), "-i", str(path), "-vn", "-ac", "1",
                              "-ar", str(RATE), "-f", "s16le", "-"], capture_output=True, timeout=TIMEOUT, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout:
        logger.info("Studio-Wellenform: nicht lesbar (%s)", out.stderr[-200:] if out.stderr else out.returncode)
        return None
    return out.stdout


def waveform(pid: str, rel: str) -> dict:
    ok = safe_rel(pid, rel, AUDIO_EXT | VIDEO_EXT)
    if not ok:
        raise NotFound()
    path = project_root(pid) / ok
    st = path.stat()
    key = hashlib.sha256(f"{ok}\0{st.st_size}\0{st.st_mtime_ns}".encode()).hexdigest()[:32]
    cache = root(pid) / "cache" / "peaks" / f"{key}.json"
    hit = read_json(cache, None)
    if isinstance(hit, dict) and isinstance(hit.get("peaks"), list):
        return hit
    pcm = _decode(path)
    if pcm is None:
        return {"per_second": PER_SECOND, "duration": 0, "peaks": []}
    out = {"per_second": PER_SECOND, "duration": round(len(pcm) / 2 / RATE, 3), "peaks": peaks_from_pcm(pcm)}
    write_json(root(pid, create=True) / "cache" / "peaks" / f"{key}.json", out)
    return out
