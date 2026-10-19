"""Dienst mit zwei Quellen: Maus → Dashboard (EVDI-Bilder), zurück zum Video, EVDI-Ausfall, Zustand in state.json."""
from __future__ import annotations

import datetime as dt
import json
import time

from PIL import Image

from renderer import main, mode
from renderer.program import Program
from test_main import FakeDisplay

def _jpeg(color) -> bytes:
    import io
    out = io.BytesIO()
    Image.new("RGB", (108, 192), color).save(out, "JPEG", quality=90)
    return out.getvalue()


JPEG_A, JPEG_B = _jpeg((255, 0, 0)), _jpeg((0, 0, 255))


class FakeDash:
    """Statt renderer.dashboard.Dashboard: Leerlauf aus einer Liste, Bilder aus einer Liste (None = keine Änderung)."""

    def __init__(self, idles, jpegs=(JPEG_A,), fail_after=None):
        self.idles, self.jpegs, self.fail_after = list(idles), list(jpegs), fail_after
        self.takes, self.closed, self.reason, self.active = 0, False, None, []
        self.last_jpeg = None

    last_input: float | None = None                 # gesetzt → Leerlauf wächst real ab diesem Zeitpunkt (wie X)

    def idle_ms(self):
        if self.last_input is not None:
            return int((time.monotonic() - self.last_input) * 1000)
        return self.idles.pop(0) if len(self.idles) > 1 else self.idles[0]

    def available(self):
        if self.fail_after is not None and self.takes > self.fail_after:
            self.reason = "EVDI-Fehler: evdi weg"
            return False
        return True

    def set_active(self, on):
        self.active.append(on)

    def take_frame(self):
        self.takes += 1
        j = self.jpegs.pop(0) if self.jpegs else None
        if j:
            self.last_jpeg = j
        return j

    def close(self):
        self.closed = True


class SentDisplay(FakeDisplay):
    def __init__(self):
        super().__init__()
        self.jpegs = []

    def send_jpeg(self, jpeg):
        super().send_jpeg(jpeg)
        self.jpegs.append(jpeg)


def _runner(tmp_path, dash, disp, **kw):
    def frames(src, w, h, fps):
        img = Image.new("RGB", (w, h), (30, 90, 30))
        while True:
            yield img
    r = main.Runner(data_dir=tmp_path, connect=lambda: disp, frames=frames, status=lambda: "ok",
                    sleep=lambda s: None, fps=24, program=lambda now: Program(video=None),
                    now=lambda: dt.datetime(2026, 10, 18, 12), check_every=0, dashboard=dash, **kw)
    r.mode_every = 0                                # im Dienst alle 0,25 s; im Test jedes Mal
    return r


def test_maus_schaltet_auf_dashboard_und_sendet_evdi_bilder(tmp_path):
    dash, disp = FakeDash([90_000, 90_000, 200], jpegs=[JPEG_A, None, JPEG_B]), SentDisplay()
    r = _runner(tmp_path, dash, disp)
    r.dashboard_repeat = 0
    r.run(max_frames=8)
    assert JPEG_A in disp.jpegs and JPEG_B in disp.jpegs
    first_dash = disp.jpegs.index(JPEG_A)
    assert first_dash > 0, "vorher lief das Video"
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["mode"] == "dashboard" and st["dashboard"] == "bereit"


def test_dashboard_ohne_aenderung_wiederholt_letztes_bild(tmp_path):
    dash, disp = FakeDash([0], jpegs=[JPEG_A]), SentDisplay()
    r = _runner(tmp_path, dash, disp)
    r.dashboard_repeat = 0
    r.run(max_frames=4)
    assert disp.jpegs.count(JPEG_A) >= 3


def test_zurueck_knopf_beendet_dashboard(tmp_path):
    dash, disp = FakeDash([0], jpegs=[JPEG_A]), SentDisplay()
    r = _runner(tmp_path, dash, disp)
    r.dashboard_repeat = 0
    r.run(max_frames=3)
    dash.last_input = time.monotonic()              # Klick auf „Zurück“ – danach keine Eingabe mehr
    mode.request_back(tmp_path)
    r.run(max_frames=12)
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["mode"] == "video"
    assert disp.jpegs[-1] != JPEG_A, "nach „Zurück“ läuft wieder das Video"


def test_evdi_faellt_aus_dann_video_und_grund(tmp_path):
    dash, disp = FakeDash([0], jpegs=[JPEG_A, JPEG_A], fail_after=2), SentDisplay()
    r = _runner(tmp_path, dash, disp)
    r.dashboard_repeat = 0
    r.run(max_frames=10)
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["mode"] == "video" and "evdi weg" in st["dashboard"]
    assert dash.active[-1] is False, "Dashboard-Thread holt danach keine Bilder mehr"


def test_ohne_dashboard_wie_bisher(tmp_path):
    disp = SentDisplay()
    r = _runner(tmp_path, None, disp)
    r.run(max_frames=3)
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["mode"] == "video" and st["dashboard"] == "aus"


def test_nachts_weckt_die_maus_auch(tmp_path):
    dash, disp = FakeDash([90_000, 100], jpegs=[JPEG_A]), SentDisplay()
    r = main.Runner(data_dir=tmp_path, connect=lambda: disp, status=lambda: "ok", sleep=lambda s: None, fps=24,
                    program=lambda now: Program(night="dim"), now=lambda: dt.datetime(2026, 10, 18, 23, 30),
                    check_every=0, dashboard=dash)
    r.mode_every, r.dashboard_repeat = 0, 0
    r.run(max_frames=4)
    assert JPEG_A in disp.jpegs


def test_chat_antwort_haelt_dashboard_im_dienst(tmp_path):
    """S6: Leerlauf weit über der Rückkehrzeit, aber Hydra antwortet (chat_busy) → Dienst bleibt im Dashboard."""
    (tmp_path / "chat_busy.json").write_text(json.dumps({"since": time.time()}))
    dash, disp = FakeDash([0, 500_000], jpegs=[JPEG_A]), SentDisplay()
    r = _runner(tmp_path, dash, disp)
    r.dashboard_repeat = 0
    r.run(max_frames=6)
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["mode"] == "dashboard"
    (tmp_path / "chat_busy.json").unlink()
    r.run(max_frames=12)
    assert json.loads((tmp_path / "state.json").read_text())["mode"] == "video", "Antwort fertig → zurück zum Video"
