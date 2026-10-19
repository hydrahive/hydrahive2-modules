"""Dashboard-Quelle für den Dienst: eigener Thread besitzt das EVDI-Gerät, dazu die Leerlaufzeit des Kiosk-X-Servers.

Warum ein Thread (gemessen auf .2): Solange niemand die EVDI-Ereignisse abarbeitet, hängt `xrandr` (18.10.); solange
niemand die Bilder abholt, wartet Xorg bei jedem Bildwechsel bis zum Timeout (19.10.: 0/s → Xorg dauerhaft blockiert,
20/s → praktisch nie, 0,9 % CPU). Der Thread holt deshalb immer ~20×/s ab – auch im Video- und Nachtmodus – und baut nur
im Dashboard-Modus (`set_active(True)`) JPEGs daraus.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from .evdi_source import EvdiSource, EvdiUnavailable

log = logging.getLogger("vitrine.dashboard")
IDLE_TICK = 0.05          # im Hintergrund ~20×/s Ereignisse + Bild abholen (0,9 % CPU gemessen)
RETRY_OPEN = 30.0


class Dashboard:
    def __init__(self, *, w: int, h: int, idle, open_source: Callable[[int, int], EvdiSource] = EvdiSource.open,
                 fps: int = 20, retry_open: float = RETRY_OPEN, tick: float = IDLE_TICK, pointer=None):
        self.w, self.h, self._idle, self._open = w, h, idle, open_source
        self._pointer = pointer                     # eigene X-Verbindung für den Thread (Xlib ist nicht threadsicher)
        self.period, self.retry_open, self.tick = 1.0 / fps, retry_open, tick
        self.reason: str | None = "startet"
        self.last_jpeg: bytes | None = None
        self._src: EvdiSource | None = None
        self._active = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._fresh: bytes | None = None
        self._thread = threading.Thread(target=self._run, name="vitrine-evdi", daemon=True)

    def start(self) -> "Dashboard":
        self._thread.start()
        return self

    # --- vom Dienst (Hauptthread) ---
    def idle_ms(self) -> int | None:
        return self._idle.idle_ms()

    def available(self) -> bool:
        src = self._src
        return src is not None and src.ready and self.reason is None

    def set_active(self, on: bool) -> None:
        (self._active.set if on else self._active.clear)()

    def take_frame(self) -> bytes | None:
        with self._lock:
            j, self._fresh = self._fresh, None
        return j

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(2)

    # --- Thread ---
    def _run(self) -> None:
        next_open = 0.0
        while not self._stop.is_set():
            if self._src is None:
                if time.monotonic() >= next_open:
                    next_open = time.monotonic() + self.retry_open
                    self._try_open()
                self._stop.wait(self.tick)
                continue
            t0 = time.monotonic()
            try:
                if self._active.is_set():
                    j = self._src.next_jpeg(cursor=self._pointer.pointer() if self._pointer else None)
                    if j:
                        with self._lock:
                            self._fresh, self.last_jpeg = j, j
                else:
                    self._src.drain()
                self.reason = None if self._src.ready else "Kiosk hat den Bildschirm noch nicht eingeschaltet"
            except OSError as e:
                log.warning("EVDI-Fehler: %s", e)
                self.reason = f"EVDI-Fehler: {e}"
                self._close_src()
                continue
            wait = self.period if self._active.is_set() else self.tick
            self._stop.wait(max(0.0, wait - (time.monotonic() - t0)))
        self._close_src()

    def _try_open(self) -> None:
        try:
            self._src = self._open(self.w, self.h)
            self.reason = "Kiosk hat den Bildschirm noch nicht eingeschaltet"
        except EvdiUnavailable as e:
            self.reason = str(e)

    def _close_src(self) -> None:
        if self._src is not None:
            try:
                self._src.close()
            except OSError:
                pass
            self._src = None
