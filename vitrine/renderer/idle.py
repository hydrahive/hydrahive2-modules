"""Leerlaufzeit des Kiosk-X-Servers (letzte Maus-/Tastatureingabe), über XScreenSaverQueryInfo per ctypes.

Am 18.10.2026 auf .2 geprüft: Trackpad-Bewegung und Klick → Leerlauf 0–300 ms. Ohne X oder ohne Zugriff → None
(dann bleibt der Dienst beim Video). Die Verbindung bleibt offen und wird bei Fehlern gedrosselt neu aufgebaut.
"""
from __future__ import annotations

import ctypes
import time
from typing import Callable


class _Info(ctypes.Structure):
    _fields_ = [("window", ctypes.c_ulong), ("state", ctypes.c_int), ("kind", ctypes.c_int),
                ("til_or_since", ctypes.c_ulong), ("idle", ctypes.c_ulong), ("event_mask", ctypes.c_ulong)]


class _XLib:
    """Echte Bibliotheken; Tests ersetzen das durch ein Objekt mit denselben fünf Methoden."""

    def __init__(self):
        self.x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self.xss = ctypes.cdll.LoadLibrary("libXss.so.1")
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_Info)]
        u, i = ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int)
        self.x11.XQueryPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong, u, u, i, i, i, i, ctypes.POINTER(ctypes.c_uint)]

    def open(self, name: bytes):
        return self.x11.XOpenDisplay(name)

    def root(self, d):
        return self.x11.XDefaultRootWindow(d)

    def query(self, d, root, info_ptr) -> int:
        return self.xss.XScreenSaverQueryInfo(d, root, info_ptr)

    def pointer(self, d, root) -> tuple[int, int] | None:
        w1, w2 = ctypes.c_ulong(), ctypes.c_ulong()
        rx, ry, wx, wy, m = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_uint()
        ok = self.x11.XQueryPointer(d, root, ctypes.byref(w1), ctypes.byref(w2), ctypes.byref(rx), ctypes.byref(ry),
                                    ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(m))
        return (rx.value, ry.value) if ok else None

    def close(self, d):
        self.x11.XCloseDisplay(d)


class Idle:
    def __init__(self, display: str = ":0", *, lib=None, retry_every: float = 5.0,
                 clock: Callable[[], float] = time.monotonic):
        self.display, self.retry_every, self.clock = display, retry_every, clock
        self.reason: str | None = None
        self._d = None
        self._root = 0
        self._next_try = 0.0
        self._info = _Info()
        try:
            self._lib = lib if lib is not None else _XLib()
        except OSError as e:
            self._lib, self.reason = None, f"X-Bibliotheken fehlen: {e}"

    def _connect(self) -> bool:
        now = self.clock()
        if now < self._next_try:
            return False
        self._next_try = now + self.retry_every
        d = self._lib.open(self.display.encode())
        if not d:
            self.reason = f"X-Server {self.display} nicht erreichbar"
            return False
        self._d, self._root, self.reason = d, self._lib.root(d), None
        return True

    def idle_ms(self) -> int | None:
        if self._lib is None:
            return None
        if self._d is None and not self._connect():
            return None
        if not self._lib.query(self._d, self._root, ctypes.pointer(self._info)):
            self._lib.close(self._d)
            self._d, self.reason = None, "Leerlauf-Abfrage fehlgeschlagen"
            return None
        return int(self._info.idle)

    def pointer(self) -> tuple[int, int] | None:
        """Zeigerposition in Bildschirmkoordinaten (der EVDI-Ausgang liegt bei +0+0) oder None."""
        fn = getattr(self._lib, "pointer", None) if self._lib is not None else None
        if fn is None or (self._d is None and not self._connect()):
            return None
        return fn(self._d, self._root)

    def close(self) -> None:
        if self._d is not None and self._lib is not None:
            self._lib.close(self._d)
        self._d = None
