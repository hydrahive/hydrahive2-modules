"""libevdi per ctypes – nur die Funktionen, die Vitrine braucht. Strukturen nach `evdi_lib.h` (libevdi 1.14);
Anbindung nach dem Vorbild von tinyscreen/evdi_wrapper.py (MIT, siehe UPSTREAM.md).

`EvdiLib` hat dieselbe kleine Oberfläche wie die Test-Attrappe: check, add, open, connect, register, unregister,
events, grab, close.
"""
from __future__ import annotations

import ctypes

AVAILABLE, UNRECOGNIZED, NOT_PRESENT = 0, 1, 2
MAX_RECTS = 16


class Rect(ctypes.Structure):
    _fields_ = [("x1", ctypes.c_int), ("y1", ctypes.c_int), ("x2", ctypes.c_int), ("y2", ctypes.c_int)]


class _Mode(ctypes.Structure):
    _fields_ = [("width", ctypes.c_int), ("height", ctypes.c_int), ("refresh_rate", ctypes.c_int),
                ("bits_per_pixel", ctypes.c_int), ("pixel_format", ctypes.c_uint)]


class _Buffer(ctypes.Structure):
    _fields_ = [("id", ctypes.c_int), ("buffer", ctypes.c_void_p), ("width", ctypes.c_int), ("height", ctypes.c_int),
                ("stride", ctypes.c_int), ("rects", ctypes.POINTER(Rect)), ("rect_count", ctypes.c_int)]


class _CursorSet(ctypes.Structure):
    _fields_ = [("hot_x", ctypes.c_int32), ("hot_y", ctypes.c_int32), ("width", ctypes.c_uint32),
                ("height", ctypes.c_uint32), ("enabled", ctypes.c_uint8), ("buffer_length", ctypes.c_uint32),
                ("buffer", ctypes.POINTER(ctypes.c_uint32)), ("pixel_format", ctypes.c_uint32), ("stride", ctypes.c_uint32)]


class _CursorMove(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


class _Ddcci(ctypes.Structure):
    _fields_ = [("address", ctypes.c_uint16), ("flags", ctypes.c_uint16), ("buffer_length", ctypes.c_uint32),
                ("buffer", ctypes.POINTER(ctypes.c_uint8))]


_INT_CB = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_void_p)
_MODE_CB = ctypes.CFUNCTYPE(None, _Mode, ctypes.c_void_p)
_CSET_CB = ctypes.CFUNCTYPE(None, _CursorSet, ctypes.c_void_p)
_CMOVE_CB = ctypes.CFUNCTYPE(None, _CursorMove, ctypes.c_void_p)
_DDC_CB = ctypes.CFUNCTYPE(None, _Ddcci, ctypes.c_void_p)


class _Context(ctypes.Structure):
    _fields_ = [("dpms", _INT_CB), ("mode_changed", _MODE_CB), ("update_ready", _INT_CB), ("crtc_state", _INT_CB),
                ("cursor_set", _CSET_CB), ("cursor_move", _CMOVE_CB), ("ddcci", _DDC_CB), ("user_data", ctypes.c_void_p)]


class EvdiLib:
    def __init__(self):
        lib = ctypes.cdll.LoadLibrary("libevdi.so.1")
        lib.evdi_check_device.argtypes, lib.evdi_check_device.restype = [ctypes.c_int], ctypes.c_int
        lib.evdi_add_device.argtypes, lib.evdi_add_device.restype = [], ctypes.c_int
        lib.evdi_open.argtypes, lib.evdi_open.restype = [ctypes.c_int], ctypes.c_void_p
        lib.evdi_close.argtypes = [ctypes.c_void_p]
        lib.evdi_connect.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint32]
        lib.evdi_disconnect.argtypes = [ctypes.c_void_p]
        lib.evdi_register_buffer.argtypes = [ctypes.c_void_p, _Buffer]
        lib.evdi_unregister_buffer.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.evdi_request_update.argtypes, lib.evdi_request_update.restype = [ctypes.c_void_p, ctypes.c_int], ctypes.c_bool
        lib.evdi_grab_pixels.argtypes = [ctypes.c_void_p, ctypes.POINTER(Rect), ctypes.POINTER(ctypes.c_int)]
        lib.evdi_handle_events.argtypes = [ctypes.c_void_p, ctypes.POINTER(_Context)]
        lib.evdi_get_event_ready.argtypes, lib.evdi_get_event_ready.restype = [ctypes.c_void_p], ctypes.c_int
        self._lib = lib
        self._rects = (Rect * MAX_RECTS)()
        self._nrects = ctypes.c_int(0)
        self._keep: list = []

    def check(self, i: int) -> int:
        return self._lib.evdi_check_device(i)

    def add(self) -> int:
        return self._lib.evdi_add_device()

    def open(self, i: int):
        return self._lib.evdi_open(i) or None

    def connect(self, h, edid: bytes, area: int) -> None:
        self._lib.evdi_connect(h, edid, len(edid), area)

    def register(self, h, buf_ptr: int, w: int, hh: int, stride: int) -> None:
        self._lib.evdi_register_buffer(h, _Buffer(0, buf_ptr, w, hh, stride, self._rects, MAX_RECTS))

    def unregister(self, h) -> None:
        self._lib.evdi_unregister_buffer(h, 0)

    def events(self, h, on_mode) -> None:
        """Wartende Ereignisse verarbeiten; on_mode(w, h, hz) bei Moduswechsel. Blockiert nicht."""
        import select
        fd = self._lib.evdi_get_event_ready(h)
        if not select.select([fd], [], [], 0)[0]:
            return
        noop = _INT_CB(lambda a, b: None)
        cbs = [noop, _MODE_CB(lambda m, u: on_mode(m.width, m.height, m.refresh_rate)), noop, noop,
               _CSET_CB(lambda c, u: None), _CMOVE_CB(lambda c, u: None), _DDC_CB(lambda d, u: None)]
        self._keep = cbs
        self._lib.evdi_handle_events(h, ctypes.byref(_Context(*cbs, None)))

    def grab(self, h) -> None:
        self._lib.evdi_request_update(h, 0)
        self._nrects.value = MAX_RECTS
        self._lib.evdi_grab_pixels(h, self._rects, ctypes.byref(self._nrects))

    def close(self, h) -> None:
        self._lib.evdi_disconnect(h)
        self._lib.evdi_close(h)
