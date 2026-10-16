"""Bildcache im Hintergrund vorberechnen (E4). Der Dienst fragt `get()`; bis der Cache fertig ist, kommt None
und er nutzt den bisherigen Weg (dekodieren + kodieren). Immer nur ein Bau gleichzeitig, mit niedriger Priorität."""
from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image

from . import framecache

RETRY_AFTER = 600.0          # nach einem Fehler erst nach 10 min erneut versuchen
NICE = 10
log = logging.getLogger("vitrine.warmer")

FramesFn = Callable[[Path, int, int, int], Iterable[Image.Image]]


def _lower_priority() -> None:
    """Nur diesen Thread (und von ihm gestartete Prozesse wie ffmpeg) niedriger einplanen – unter Linux ist der
    nice-Wert pro Thread."""
    try:
        os.setpriority(os.PRIO_PROCESS, threading.get_native_id(), NICE)
    except (OSError, AttributeError):
        pass


class Warmer:
    def __init__(self, cache_dir: Path, *, frames: FramesFn, clock: Callable[[], float] = time.monotonic):
        self.cache_dir, self._frames, self._clock = cache_dir, frames, clock
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._failed: dict[str, float] = {}
        self._status = {"state": None, "video": None, "done": 0, "error": None}

    def busy(self) -> bool:
        t = self._thread
        return t is not None and t.is_alive()

    def status(self) -> dict:
        with self._lock:
            return dict(self._status)

    def get(self, src: Path, w: int, h: int, fps: int, quality: int) -> framecache.FrameCache | None:
        try:
            c = framecache.open_cache(src, self.cache_dir, w, h, fps, quality)
        except OSError:
            return None
        if c is not None:
            with self._lock:
                if self._status.get("state") != "building":
                    self._status = {"state": "ready", "video": src.name, "done": len(c), "error": None}
            return c
        self._maybe_start(src, w, h, fps, quality)
        return None

    def _maybe_start(self, src: Path, w: int, h: int, fps: int, quality: int) -> None:
        if not src.is_file() or self.busy():
            return
        k = framecache.key(src, w, h, fps, quality)
        if self._clock() - self._failed.get(k, -1e18) < RETRY_AFTER:
            return
        with self._lock:
            self._status = {"state": "building", "video": src.name, "done": 0, "error": None}
        self._thread = threading.Thread(target=self._build, args=(src, w, h, fps, quality, k),
                                        name="vitrine-cache", daemon=True)
        self._thread.start()

    def _progress(self, n: int) -> None:
        with self._lock:
            self._status["done"] = n

    def _build(self, src: Path, w: int, h: int, fps: int, quality: int, k: str) -> None:
        _lower_priority()
        t0 = time.monotonic()
        try:
            framecache.build(src, self.cache_dir, w, h, fps, quality,
                             frames=lambda: self._frames(src, w, h, fps), progress=self._progress)
        except Exception as e:                      # Dienst muss weiterlaufen, egal was beim Vorberechnen passiert
            log.warning("Bildcache für %s fehlgeschlagen: %s", src.name, e)
            self._failed[k] = self._clock()
            with self._lock:
                self._status.update(state="error", error=str(e)[:200])
            return
        log.info("Bildcache für %s fertig in %.1f s", src.name, time.monotonic() - t0)
        with self._lock:
            self._status.update(state="ready")
