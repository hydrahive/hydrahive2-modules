"""Mauszeiger im Dashboard-Bild: EVDI liefert ihn nicht mit (am Gerät gesehen) – Vitrine zeichnet ihn selbst."""
from __future__ import annotations

import ctypes
import io

from PIL import Image

from renderer import cursor, idle
from test_evdi_source import FakeEvdi, W, H
from renderer import evdi_source as es


def test_zeiger_wird_an_der_position_gezeichnet():
    img = Image.new("RGB", (200, 300), (0, 0, 0))
    cursor.draw(img, (50, 80))
    assert img.getpixel((54, 100)) == cursor.FILL               # mitten im Pfeil (Rand ist schwarz)
    assert img.getpixel((150, 250)) == (0, 0, 0)


def test_zeiger_am_rand_ohne_fehler():
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    cursor.draw(img, (99, 99))
    cursor.draw(img, (-20, 500))


def test_nur_zeigerbewegung_gilt_als_aenderung():
    f = FakeEvdi()
    s = es.EvdiSource.open(W, H, lib=f)
    a = s.next_jpeg(cursor=(10, 10))
    assert a is not None
    assert s.next_jpeg(cursor=(10, 10)) is None
    b = s.next_jpeg(cursor=(100, 200))
    assert b is not None
    px = Image.open(io.BytesIO(b)).convert("RGB").getpixel((104, 220))
    assert sum(px) > 600, "weißer Zeiger an der neuen Stelle"


class PointerX:
    def open(self, name):
        return 1

    def root(self, d):
        return 7

    def query(self, d, root, info):
        return 1

    def pointer(self, d, root):
        return (321, 654)

    def close(self, d):
        pass


def test_idle_liefert_zeigerposition():
    assert idle.Idle(":0", lib=PointerX()).pointer() == (321, 654)


def test_idle_ohne_zeigerfunktion_none():
    class Ohne(PointerX):
        pointer = None
    assert idle.Idle(":0", lib=Ohne()).pointer() is None


def test_ctypes_signatur_xquerypointer_vorhanden():
    assert hasattr(idle._XLib, "pointer")
    assert ctypes.sizeof(ctypes.c_ulong) >= 4
