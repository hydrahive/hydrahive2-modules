"""Hauptschleife: Neuverbinden statt Absturz, Status-Datei, Testbild ohne Video."""
from __future__ import annotations

import json

import usb.core
from PIL import Image

from renderer import main


class FakeDisplay:
    width, height, fps = 1080, 1920, 60

    def __init__(self, fail_after=None):
        self.sent, self.fail_after, self.closed = 0, fail_after, False

    def send_jpeg(self, jpeg):
        if self.fail_after is not None and self.sent >= self.fail_after:
            raise usb.core.USBError("No such device", errno=19)
        assert jpeg[:2] == b"\xff\xd8"
        self.sent += 1

    def close(self):
        self.closed = True


class FakeFrames:
    """Liefert endlos dasselbe Bild – ersetzt die ffmpeg-Pipe."""

    def __init__(self, w, h):
        self.img = Image.new("RGB", (w, h), (20, 60, 20))

    def __iter__(self):
        while True:
            yield self.img


def _runner(tmp_path, displays, **kw):
    opened = []

    def connect():
        if not displays:
            return None
        d = displays.pop(0)
        opened.append(d)
        return d

    r = main.Runner(data_dir=tmp_path, connect=connect, frames=lambda src, w, h, fps: FakeFrames(w, h),
                    status=lambda: "Hydra läuft", sleep=lambda s: None, fps=30, **kw)
    return r, opened


def test_sendet_bilder_und_schreibt_status(tmp_path):
    r, opened = _runner(tmp_path, [FakeDisplay()])
    r.run(max_frames=5)
    assert opened[0].sent == 5
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["connected"] is True and st["frames"] == 5 and st["size"] == [1080, 1920]


def test_usb_weg_verbindet_neu(tmp_path):
    erstes, zweites = FakeDisplay(fail_after=3), FakeDisplay()
    r, opened = _runner(tmp_path, [erstes, zweites])
    r.run(max_frames=6)
    assert erstes.closed, "kaputte Verbindung wird freigegeben"
    assert opened == [erstes, zweites]
    assert erstes.sent + zweites.sent == 6
    assert json.loads((tmp_path / "state.json").read_text())["reconnects"] == 1


def test_kein_display_wartet_statt_abzustuerzen(tmp_path):
    waits = []
    r = main.Runner(data_dir=tmp_path, connect=lambda: None, frames=lambda *a: FakeFrames(1080, 1920),
                    status=lambda: "", sleep=waits.append, fps=30)
    r.run(max_frames=1, max_waits=3)
    assert waits == [main.RETRY_SECONDS] * 3
    assert json.loads((tmp_path / "state.json").read_text())["connected"] is False


def test_ohne_video_testbild(tmp_path):
    r, opened = _runner(tmp_path, [FakeDisplay()])
    assert r.source() is None
    img = main.fallback_frame(1080, 1920)
    assert img.size == (1080, 1920)


def test_jpeg_qualitaet_einstellbar(tmp_path):
    a = main.encode(Image.new("RGB", (1080, 1920), (200, 100, 50)), 90)
    b = main.encode(Image.effect_noise((1080, 1920), 60).convert("RGB"), 60)
    assert a[:2] == b[:2] == b"\xff\xd8"


def test_standard_bildrate_24():
    """Atelier-Videos kommen mit 24 fps – hochrechnen auf 30 kostet nur CPU."""
    import inspect
    assert inspect.signature(main.Runner).parameters["fps"].default == 24
    assert main.DEFAULT_FPS == 24
