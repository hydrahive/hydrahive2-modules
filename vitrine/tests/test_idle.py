"""Leerlaufzeit des Kiosk-X-Servers: Werte, X weg → None, Wiederverbinden. Mit gefälschter Bibliothek."""
from __future__ import annotations

import ctypes

from renderer import idle


class FakeX:
    """Spielt libX11 + libXss nach (nur was idle.py nutzt)."""

    def __init__(self, values, opens=None):
        self.values, self.opens, self.closed = list(values), list(opens or [1]), 0

    def open(self, name: bytes):
        return self.opens.pop(0) if self.opens else 1

    def root(self, d):
        return 7

    def query(self, d, root, info_ptr) -> int:
        if not self.values:
            return 0
        v = self.values.pop(0)
        if v is None:
            return 0                                     # Abfrage fehlgeschlagen (X weg)
        info_ptr.contents.idle = v
        return 1

    def close(self, d):
        self.closed += 1


def test_liest_leerlauf():
    x = FakeX([5000, 120])
    i = idle.Idle(":0", lib=x)
    assert i.idle_ms() == 5000 and i.idle_ms() == 120


def test_kein_x_dann_none_und_spaeter_wieder():
    x = FakeX([300], opens=[0, 0, 1])
    i = idle.Idle(":0", lib=x, retry_every=0)
    assert i.idle_ms() is None
    assert i.idle_ms() is None
    assert i.idle_ms() == 300


def test_abfrage_fehlgeschlagen_verbindet_neu():
    x = FakeX([None, 42])
    i = idle.Idle(":0", lib=x, retry_every=0)
    assert i.idle_ms() is None and x.closed == 1
    assert i.idle_ms() == 42


def test_wiederholung_gedrosselt():
    t = {"now": 0.0}
    x = FakeX([], opens=[0, 1])
    i = idle.Idle(":0", lib=x, retry_every=5, clock=lambda: t["now"])
    assert i.idle_ms() is None
    t["now"] = 2
    assert i.idle_ms() is None and x.opens == [1]          # noch nicht erneut versucht


def test_ohne_bibliothek_nie_verfuegbar(monkeypatch):
    def kaputt(name):
        raise OSError("nicht da")
    monkeypatch.setattr(ctypes.cdll, "LoadLibrary", kaputt)
    i = idle.Idle(":0")
    assert i.idle_ms() is None and i.reason and "nicht da" in i.reason
