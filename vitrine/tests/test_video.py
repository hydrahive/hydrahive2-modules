"""Video-Auswahl und Schleifen-Cache (ffmpeg wird für die Tests gestubbt)."""
from __future__ import annotations

import os
import time

from renderer import video


def _f(p, size=10):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * size)
    return p


def test_auswahl_leer(tmp_path):
    assert video.pick(tmp_path / "fehlt") is None
    (tmp_path / "v").mkdir()
    assert video.pick(tmp_path / "v") is None


def test_auswahl_nur_videos_sortiert(tmp_path):
    d = tmp_path / "v"
    _f(d / "b.mp4"); _f(d / "a.webm"); _f(d / "notiz.txt"); _f(d / "bild.jpg"); _f(d / ".versteckt.mp4")
    assert video.pick(d).name == "a.webm"


def test_cache_name_haengt_an_quelle_und_parametern(tmp_path):
    src = _f(tmp_path / "v" / "herbst.mp4", 100)
    a = video.cache_path(src, tmp_path / "c", 1080, 1920, 30)
    assert a == video.cache_path(src, tmp_path / "c", 1080, 1920, 30)
    assert a != video.cache_path(src, tmp_path / "c", 1080, 1920, 25)
    os.utime(src, (time.time() + 100, time.time() + 100))
    assert a != video.cache_path(src, tmp_path / "c", 1080, 1920, 30), "geänderte Quelle → neuer Cache"


def test_prepare_baut_nur_einmal(tmp_path, monkeypatch):
    src = _f(tmp_path / "v" / "herbst.mp4")
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        _f(__import__("pathlib").Path(cmd[-1]))
        class R: returncode = 0
        return R()

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    monkeypatch.setattr(video, "duration", lambda p: 10.0)
    out1 = video.prepare(src, tmp_path / "c", 1080, 1920, 30)
    out2 = video.prepare(src, tmp_path / "c", 1080, 1920, 30)
    assert out1 == out2 and out1.exists() and len(calls) == 1
    cmd = " ".join(calls[0])
    assert "scale=1080:1920" in cmd and "fps=30" in cmd and "xfade" in cmd and "-an" in calls[0]


def test_prepare_raeumt_alte_caches(tmp_path, monkeypatch):
    src = _f(tmp_path / "v" / "herbst.mp4")
    alt = _f(tmp_path / "c" / "herbst-alt.mp4")
    fremd = _f(tmp_path / "c" / "anderes-abc.mp4")

    def fake_run(cmd, **kw):
        _f(__import__("pathlib").Path(cmd[-1]))
        class R: returncode = 0
        return R()

    monkeypatch.setattr(video.subprocess, "run", fake_run)
    monkeypatch.setattr(video, "duration", lambda p: 10.0)
    video.prepare(src, tmp_path / "c", 1080, 1920, 30)
    assert not alt.exists(), "alter Cache derselben Quelle wird entfernt"
    assert fremd.exists(), "Cache anderer Videos bleibt"


def test_kurzes_video_ohne_ueberblendung(tmp_path, monkeypatch):
    src = _f(tmp_path / "v" / "kurz.mp4")
    calls = []
    monkeypatch.setattr(video.subprocess, "run", lambda cmd, **kw: (calls.append(cmd), _f(__import__("pathlib").Path(cmd[-1])), type("R", (), {"returncode": 0})())[2])
    monkeypatch.setattr(video, "duration", lambda p: 1.5)
    video.prepare(src, tmp_path / "c", 1080, 1920, 30)
    assert "xfade" not in " ".join(calls[0])


def test_dekodieren_mit_einem_thread(monkeypatch):
    """Gemessen auf hhmaster (24 Threads): -threads 0 kostet 6,0 s CPU je 300 Bilder, -threads 1 nur 2,3 s."""
    seen = {}

    class P:
        stdout = __import__("io").BytesIO(b"")
        def kill(self): pass
        def wait(self, timeout=None): pass

    monkeypatch.setattr(video.subprocess, "Popen", lambda cmd, **kw: (seen.setdefault("cmd", cmd), P())[1])
    list(video.frames(__import__("pathlib").Path("x.mp4"), 4, 4, 24))
    cmd = seen["cmd"]
    assert cmd[cmd.index("-threads") + 1] == "1" and cmd.index("-threads") < cmd.index("-i")
