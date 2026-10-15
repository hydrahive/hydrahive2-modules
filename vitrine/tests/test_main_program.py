"""Dienst + Programm: Wechsel bei neuem Programm, Nachtmodus mit 1 Bild/s, Vorschau-Datei, Feiertagsname."""
from __future__ import annotations

import datetime as dt
import json

from PIL import Image

from renderer import main
from renderer.program import Program
from test_main import FakeDisplay


class Uhr:
    def __init__(self, start):
        self.t = start

    def __call__(self):
        return self.t


def _runner(tmp_path, programs, uhr, sleeps, frames_seen):
    it = iter(programs)
    cur = {"p": next(it)}

    def program_fn(now):
        return cur["p"]

    def frames(src, w, h, fps):
        frames_seen.append(src)
        img = Image.new("RGB", (w, h), (30, 90, 30))
        n = 0
        while True:
            n += 1
            if n % 3 == 0:                       # nach 3 Bildern wechselt das Programm (falls noch eins kommt)
                cur["p"] = next(it, cur["p"])
            yield img

    r = main.Runner(data_dir=tmp_path, connect=lambda: FakeDisplay(), frames=frames, status=lambda: "ok",
                    sleep=sleeps.append, fps=24, program=program_fn, now=uhr, check_every=0)
    return r


def test_wechsel_bei_neuem_programm(tmp_path):
    a = Program(video=tmp_path / "videos" / "herbst.mp4", rule="Herbst")
    b = Program(video=tmp_path / "videos" / "weihnachten.mp4", rule="Weihnachten", holiday="Weihnachten")
    seen, sleeps = [], []
    r = _runner(tmp_path, [a, b], Uhr(dt.datetime(2026, 12, 24, 12)), sleeps, seen)
    r.run(max_frames=8)
    assert [s.name for s in seen] == ["herbst.mp4", "weihnachten.mp4"]
    st = json.loads((tmp_path / "state.json").read_text())
    assert st["video"] == "weihnachten.mp4" and st["rule"] == "Weihnachten" and st["holiday"] == "Weihnachten"


def test_nachtmodus_ein_bild_pro_sekunde(tmp_path):
    seen, sleeps = [], []
    r = _runner(tmp_path, [Program(night="dim")], Uhr(dt.datetime(2026, 10, 15, 23, 30)), sleeps, seen)
    r.run(max_frames=3)
    assert seen == [], "nachts wird kein Video dekodiert"
    assert sleeps and min(sleeps) >= 0.9
    assert json.loads((tmp_path / "state.json").read_text())["night"] == "dim"


def test_vorschau_wird_geschrieben(tmp_path):
    seen, sleeps = [], []
    r = _runner(tmp_path, [Program(video=None)], Uhr(dt.datetime(2026, 10, 15, 12)), sleeps, seen)
    r.preview_every = 0
    r.run(max_frames=2)
    with Image.open(tmp_path / "preview.jpg") as img:
        assert img.size == (270, 480)


def test_feiertagsname_im_overlay():
    from renderer import scene
    o = scene.Overlay(1080, 1920)
    t = dt.datetime(2026, 12, 24, 18, 0).timetuple()
    ohne = o.render(t, "x")
    mit = scene.Overlay(1080, 1920).render(t, "x", holiday="Weihnachten")
    a, b = ohne.getchannel("A"), mit.getchannel("A")
    assert a.crop((0, 430, 1080, 560)).getbbox() is None
    assert b.crop((0, 430, 1080, 560)).getbbox() is not None, "Feiertagsname steht unter dem Datum"


def test_feiertag_landet_im_gesendeten_bild(tmp_path, monkeypatch):
    """Der Dienst gibt den Feiertagsnamen an das Overlay weiter (nicht nur die Szene kann ihn zeichnen)."""
    from renderer import scene
    seen = []
    orig = scene.Overlay.render

    def spy(self, t, status, holiday=None):
        seen.append(holiday)
        return orig(self, t, status, holiday)

    monkeypatch.setattr(scene.Overlay, "render", spy)
    p = Program(video=tmp_path / "videos" / "w.mp4", rule="Weihnachten", holiday="Weihnachten")
    r = _runner(tmp_path, [p], Uhr(dt.datetime(2026, 12, 24, 12)), [], [])
    r.run(max_frames=2)
    assert seen and set(seen) == {"Weihnachten"}
