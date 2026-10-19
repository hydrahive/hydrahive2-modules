"""Bildquelle „Dashboard“: der virtuelle Monitor (EVDI) als JPEG für das Display – nur wenn sich der Inhalt ändert.

Gemessen am 18.10.2026 auf .2: ruhige Seite ≈ 3 % eines Kerns, Vollbild-Video ≈ 13 %.
"""
from __future__ import annotations

import ctypes
import io
import zlib

from PIL import Image

from . import cursor as pointer_img
from . import edid
from .evdi_lib import AVAILABLE, NOT_PRESENT, UNRECOGNIZED, EvdiLib  # noqa: F401 - Werte auch für Tests

MAX_DEVICES = 16


class EvdiUnavailable(RuntimeError):
    """EVDI-Modul oder libevdi fehlt – der Dienst bleibt dann beim Video."""


class EvdiSource:
    def __init__(self, lib, handle, w: int, h: int, quality: int):
        self._lib, self._h, self.w, self.h, self.quality = lib, handle, w, h, quality
        self._buf = (ctypes.c_ubyte * (w * h * 4))()
        self._ptr = ctypes.addressof(self._buf)
        self._crc: int | None = None
        self._registered = False
        self.ready = False
        self.last_jpeg: bytes | None = None

    @classmethod
    def open(cls, w: int, h: int, *, lib=None, quality: int = 85) -> "EvdiSource":
        try:
            lib = lib if lib is not None else EvdiLib()
        except OSError as e:
            raise EvdiUnavailable(f"libevdi fehlt: {e}") from e
        idx = next((i for i in range(MAX_DEVICES) if lib.check(i) == AVAILABLE), -1)
        if idx < 0:
            if lib.add() < 0:
                raise EvdiUnavailable("kein EVDI-Gerät – Kernel-Modul evdi geladen?")
            idx = next((i for i in range(MAX_DEVICES) if lib.check(i) == AVAILABLE), -1)
        handle = lib.open(idx) if idx >= 0 else None
        if not handle:
            raise EvdiUnavailable("EVDI-Gerät lässt sich nicht öffnen – Kernel-Modul evdi geladen?")
        lib.connect(handle, edid.build(w, h), w * h)
        src = cls(lib, handle, w, h, quality)
        src._register()
        return src

    def _register(self) -> None:
        if self._registered:
            self._lib.unregister(self._h)
        self._lib.register(self._h, self._ptr, self.w, self.h, self.w * 4)
        self._registered = True

    def _on_mode(self, w: int, h: int, hz: int) -> None:
        if self.ready:
            self._register()                     # alter Puffer ist nach einem Moduswechsel ungültig
        self.ready = True

    def poll_events(self) -> None:
        """Nur Ereignisse abarbeiten (ohne Bild) – nötig, damit xrandr beim Einschalten nicht hängt."""
        self._lib.events(self._h, self._on_mode)

    def drain(self) -> None:
        """Bild abholen, aber nichts damit tun. Nötig auch wenn das Dashboard gerade nicht gezeigt wird: Ohne Abholen wartet
        Xorg bei jedem Bildwechsel bis zum Timeout (flip_done, 10 s) – gemessen am 19.10.2026 auf .2, X hing bis 20 s."""
        self._lib.events(self._h, self._on_mode)
        if self.ready:
            self._lib.grab(self._h)

    def next_jpeg(self, cursor: tuple[int, int] | None = None) -> bytes | None:
        """Neues JPEG, wenn sich Bild oder Zeigerposition geändert haben, sonst None (auch vor dem ersten Modus)."""
        self._lib.events(self._h, self._on_mode)
        if not self.ready:
            return None
        self._lib.grab(self._h)
        crc = zlib.crc32(repr(cursor).encode(), zlib.crc32(self._buf))
        if crc == self._crc:
            return None
        self._crc = crc
        img = Image.frombuffer("RGB", (self.w, self.h), self._buf, "raw", "BGRX", self.w * 4, 1)
        if cursor is not None:
            img = img.copy()                       # frombuffer teilt sich den Speicher mit EVDI
            pointer_img.draw(img, cursor)
        out = io.BytesIO()
        img.save(out, "JPEG", quality=self.quality)
        self.last_jpeg = out.getvalue()
        return self.last_jpeg

    def close(self) -> None:
        if self._h:
            if self._registered:
                self._lib.unregister(self._h)
            self._lib.close(self._h)
            self._h = None
