"""ffmpeg ausführen (Spec „Bauplan 4d“, 7c): Fortschritt aus `-progress pipe:1`, Zeitgrenze, Abbrechen.

Ein Wächter-Thread beendet ffmpeg bei Zeitüberschreitung oder Abbruch – auch wenn ffmpeg nichts ausgibt (z. B. bei
einer kaputten Bilddatei); die Prüfung im Lese-Schleife allein griff dann nie. Ausgelagert aus render.py.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from collections.abc import Callable

from . import jobs, render_args

logger = logging.getLogger("hhmod_studio.render")
WATCH = 0.25                                  # so oft prüft der Wächter Zeitgrenze und Abbruch


class RenderFailed(RuntimeError):
    """ffmpeg fehlt, bricht ab oder überschreitet die Zeitgrenze."""


def has_audio(path) -> bool:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                              str(path)], capture_output=True, text=True, timeout=30, check=False)
        return bool(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _watch(proc: subprocess.Popen, limit: float, stop: Callable[[], bool] | None, why: list[str]) -> None:
    started = time.monotonic()
    while proc.poll() is None:
        if time.monotonic() - started > limit:
            why.append("timeout")
        elif stop is not None and stop():
            why.append("cancelled")
        if why:
            proc.kill()
            return
        time.sleep(WATCH)


def run(cmd: list[str], seconds: float, progress: Callable[[float], None], stop: Callable[[], bool] | None = None) -> None:
    """ffmpeg laufen lassen. `progress(f)` mit 0…0,99; `stop()` → wahr: abbrechen (jobs.Cancelled)."""
    if not shutil.which(cmd[0]):
        raise RenderFailed()
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as e:
        raise RenderFailed() from e
    why: list[str] = []
    watcher = threading.Thread(target=_watch, args=(proc, render_args.time_limit(seconds), stop, why), daemon=True,
                               name="studio-ffmpeg-watch")
    watcher.start()
    try:
        for line in proc.stdout or []:
            if line.startswith("out_time_us=") and seconds > 0:
                try:
                    progress(min(0.99, int(line.split("=", 1)[1]) / 1e6 / seconds))
                except ValueError:
                    pass
        code = proc.wait()
    except BaseException:                      # z. B. Abbrechen aus dem Fortschritt: ffmpeg sofort beenden
        proc.kill()
        proc.wait(timeout=10)
        raise
    finally:
        watcher.join(timeout=5)
    if "cancelled" in why:
        raise jobs.Cancelled()
    if why or code != 0:
        logger.warning("Studio-Film: ffmpeg %s: %s", why[0] if why else f"Code {code}",
                       (proc.stderr.read() if proc.stderr else "")[-800:])
        raise RenderFailed()
