"""Hintergrund-Vorberechnung des Bildcaches: startet einmal, meldet Fortschritt, wiederholt Fehler nicht sofort."""
from __future__ import annotations

import threading
import time

import pytest
from PIL import Image

from renderer import framecache as fc
from renderer import warmer as wm

W, H = 64, 48


@pytest.fixture
def src(tmp_path):
    p = tmp_path / "videos" / "herbst.mp4"
    p.parent.mkdir()
    p.write_bytes(b"VIDEO")
    return p


def _frames(n=4, gate: threading.Event | None = None, fail=False):
    def make(src, w, h, fps):
        def gen():
            for i in range(n):
                if gate is not None:
                    gate.wait(5)
                if fail and i == 2:
                    raise RuntimeError("ffmpeg kaputt")
                yield Image.new("RGB", (w, h), (i * 50, 0, 0))
        return gen()
    return make


def _wait(w: wm.Warmer, timeout=5.0):
    end = time.time() + timeout
    while w.busy() and time.time() < end:
        time.sleep(0.01)
    assert not w.busy()


def test_ohne_cache_none_und_baut_im_hintergrund(src, tmp_path):
    w = wm.Warmer(tmp_path / "cache", frames=_frames())
    assert w.get(src, W, H, 24, 80) is None
    _wait(w)
    c = w.get(src, W, H, 24, 80)
    assert c is not None and len(c) == 4
    c.close()
    assert w.status() == {"state": "ready", "video": "herbst.mp4", "done": 4, "error": None}


def test_startet_nur_einmal(src, tmp_path):
    gate = threading.Event()
    calls = []
    inner = _frames(gate=gate)

    def frames(*a):
        calls.append(a)
        return inner(*a)
    w = wm.Warmer(tmp_path / "cache", frames=frames)
    for _ in range(5):
        assert w.get(src, W, H, 24, 80) is None
    assert w.status()["state"] == "building"
    gate.set()
    _wait(w)
    assert len(calls) == 1


def test_fehler_wird_gemeldet_und_nicht_sofort_wiederholt(src, tmp_path):
    calls = []
    inner = _frames(fail=True)

    def frames(*a):
        calls.append(a)
        return inner(*a)
    clock = {"t": 1000.0}
    w = wm.Warmer(tmp_path / "cache", frames=frames, clock=lambda: clock["t"])
    w.get(src, W, H, 24, 80)
    _wait(w)
    st = w.status()
    assert st["state"] == "error" and "ffmpeg kaputt" in st["error"]
    assert w.get(src, W, H, 24, 80) is None
    assert not w.busy(), "kein sofortiger Neuversuch (es läuft kein neuer Bau)"
    _wait(w)
    assert len(calls) == 1
    clock["t"] += wm.RETRY_AFTER + 1
    w.get(src, W, H, 24, 80)
    _wait(w)
    assert len(calls) == 2


def test_fehlendes_video_startet_nichts(tmp_path):
    calls = []
    w = wm.Warmer(tmp_path / "cache", frames=lambda *a: calls.append(a) or iter([]))
    assert w.get(tmp_path / "gibtsnicht.mp4", W, H, 24, 80) is None
    assert calls == [] and not w.busy()


def test_neues_video_waehrend_des_baus_wartet(src, tmp_path):
    other = src.with_name("winter.mp4")
    other.write_bytes(b"W")
    gate = threading.Event()
    w = wm.Warmer(tmp_path / "cache", frames=_frames(gate=gate))
    w.get(src, W, H, 24, 80)
    assert w.get(other, W, H, 24, 80) is None
    assert w.status()["video"] == "herbst.mp4", "immer nur ein Bau gleichzeitig"
    gate.set()
    _wait(w)
    w.get(other, W, H, 24, 80)
    _wait(w)
    assert fc.open_cache(other, tmp_path / "cache", W, H, 24, 80) is not None


def test_niedrige_prioritaet_im_bau_thread(src, tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(wm, "_lower_priority", lambda: seen.append(threading.get_ident()))
    w = wm.Warmer(tmp_path / "cache", frames=_frames())
    w.get(src, W, H, 24, 80)
    _wait(w)
    assert seen and seen[0] != threading.get_ident(), "nur der Bau-Thread, nicht der Dienst"


def test_vorhandener_cache_meldet_ready(src, tmp_path):
    """Nach einem Neustart liegt der Cache schon auf der Platte – Status muss 'ready' zeigen, nicht None.
    (Live auf .226: state.json zeigte cache=None, obwohl aus dem Cache gespielt wurde.)"""
    fc.build(src, tmp_path / "cache", W, H, 24, 80, frames=lambda: iter([Image.new("RGB", (W, H))] * 3))
    w = wm.Warmer(tmp_path / "cache", frames=_frames())
    assert w.status()["state"] is None
    c = w.get(src, W, H, 24, 80)
    assert c is not None
    c.close()
    assert w.status() == {"state": "ready", "video": "herbst.mp4", "done": 3, "error": None}
    assert not w.busy(), "nichts neu gebaut"
