"""Bild des virtuellen Monitors (EVDI): nur Änderungen als JPEG, Moduswechsel, fehlende Bibliothek. Gefälschtes libevdi."""
from __future__ import annotations

import ctypes
import io

import pytest
from PIL import Image

from renderer import evdi_source as es

W, H = 320, 640


class FakeEvdi:
    """Spielt libevdi nach: Gerät 0 frei, Puffer wird bei grab mit der aktuellen Farbe gefüllt."""

    def __init__(self, *, devices=(es.AVAILABLE,), modes=((W, H, 60),)):
        self.devices, self.modes = list(devices), list(modes)
        self.color = (10, 20, 30)
        self.buf = None
        self.calls: list[str] = []
        self.connected_edid = None

    def check(self, i):
        return self.devices[i] if i < len(self.devices) else es.NOT_PRESENT

    def add(self):
        self.calls.append("add")
        self.devices.append(es.AVAILABLE)
        return 1

    def open(self, i):
        self.calls.append(f"open{i}")
        return 99

    def connect(self, h, edid, area):
        self.connected_edid = edid

    def register(self, h, buf_ptr, w, hh, stride):
        self.buf = (ctypes.c_ubyte * (w * hh * 4)).from_address(buf_ptr)
        self.calls.append("register")

    def unregister(self, h):
        self.calls.append("unregister")

    def events(self, h, on_mode):
        while self.modes:
            on_mode(*self.modes.pop(0))

    def grab(self, h):
        self.calls.append("grab")
        b, g, r = self.color[2], self.color[1], self.color[0]
        self.buf[:] = bytes([b, g, r, 0]) * (len(self.buf) // 4)

    def close(self, h):
        self.calls.append("close")


def _src(fake, **kw):
    return es.EvdiSource.open(W, H, lib=fake, **kw)


def test_erstes_bild_dann_nur_bei_aenderung():
    f = FakeEvdi()
    s = _src(f)
    j = s.next_jpeg()
    assert j and j[:2] == b"\xff\xd8"
    px = Image.open(io.BytesIO(j)).convert("RGB").getpixel((5, 5))
    assert all(abs(a - b) < 6 for a, b in zip(px, (10, 20, 30)))
    assert s.next_jpeg() is None
    f.color = (200, 100, 0)
    assert s.next_jpeg() is not None


def test_vor_dem_ersten_modus_kein_bild():
    f = FakeEvdi(modes=())
    s = _src(f)
    assert s.next_jpeg() is None and not s.ready


def test_moduswechsel_registriert_puffer_neu():
    f = FakeEvdi(modes=((W, H, 60), (W, H, 60)))
    s = _src(f)
    s.next_jpeg()
    assert f.calls.count("register") == 2 and "unregister" in f.calls


def test_legt_geraet_an_wenn_keins_frei_und_sendet_edid():
    f = FakeEvdi(devices=(es.UNRECOGNIZED,))
    s = _src(f)
    assert "add" in f.calls and "open1" in f.calls
    assert f.connected_edid[:8] == b"\x00\xff\xff\xff\xff\xff\xff\x00"
    s.close()
    assert f.calls[-1] == "close"


def test_ohne_bibliothek_unavailable(monkeypatch):
    def kaputt(name):
        raise OSError("libevdi fehlt")
    monkeypatch.setattr(ctypes.cdll, "LoadLibrary", kaputt)
    with pytest.raises(es.EvdiUnavailable, match="libevdi"):
        es.EvdiSource.open(W, H)


def test_kein_geraet_anlegbar_unavailable():
    f = FakeEvdi(devices=(es.UNRECOGNIZED,))
    f.add = lambda: -1
    with pytest.raises(es.EvdiUnavailable, match="Modul"):
        _src(f)


def test_drain_holt_ab_ohne_jpeg():
    f = FakeEvdi()
    s = _src(f)
    s.drain()
    grabs = f.calls.count("grab")
    assert s.ready and s.last_jpeg is None
    f.color = (1, 2, 3)
    s.drain()
    assert s.last_jpeg is None
