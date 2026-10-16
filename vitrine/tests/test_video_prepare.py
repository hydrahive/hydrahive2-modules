"""Vorbereiten eines Videos aus mehreren Threads/Prozessen: Sperre, eigene Zwischendatei, Aufräumen."""
from __future__ import annotations

from renderer import video


def _f(p, size=10):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * size)
    return p


def test_prepare_gleichzeitig_aus_zwei_threads(tmp_path, monkeypatch):
    """Dienst und Bildcache-Bau wollen dieselbe Datei vorbereiten: beide bekommen sie, nur einer rechnet um.
    (Live auf .226: FileNotFoundError beim Umbenennen der gemeinsamen .tmp-Datei.)"""
    import threading
    import time as _t
    src = _f(tmp_path / "v" / "herbst.mp4")
    calls, go = [], threading.Event()

    def slow_run(cmd, **kw):
        calls.append(cmd)
        go.set()
        _t.sleep(0.2)                         # zweiter Thread kommt währenddessen an
        _f(__import__("pathlib").Path(cmd[-1]))
        class R: returncode = 0
        return R()

    monkeypatch.setattr(video.subprocess, "run", slow_run)
    monkeypatch.setattr(video, "duration", lambda p: 10.0)
    results, errors = [], []

    def worker():
        try:
            results.append(video.prepare(src, tmp_path / "c", 1080, 1920, 24))
        except Exception as e:                # noqa: BLE001 - Test sammelt jeden Fehler
            errors.append(e)

    a = threading.Thread(target=worker)
    a.start()
    go.wait(5)
    b = threading.Thread(target=worker)
    b.start()
    a.join(10)
    b.join(10)
    assert errors == [] and len(results) == 2 and results[0] == results[1] and results[0].exists()
    assert len(calls) == 1, "nur einmal umgerechnet"
    assert not list((tmp_path / "c").glob("*.tmp*")), "keine Reste"


def test_prepare_fehler_hinterlaesst_keine_reste(tmp_path, monkeypatch):
    src = _f(tmp_path / "v" / "herbst.mp4")

    def boom(cmd, **kw):
        _f(__import__("pathlib").Path(cmd[-1]))     # ffmpeg hat schon angefangen zu schreiben
        raise video.subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(video.subprocess, "run", boom)
    monkeypatch.setattr(video, "duration", lambda p: 10.0)
    import pytest as _pt
    with _pt.raises(video.subprocess.CalledProcessError):
        video.prepare(src, tmp_path / "c", 1080, 1920, 24)
    assert list((tmp_path / "c").iterdir()) == []


def test_zwischendatei_gehoert_dem_prozess(tmp_path, monkeypatch):
    """Zwei Prozesse (z. B. alter und neuer Dienst beim Update) teilen sich keine Sperre – darum trägt die
    Zwischendatei die Prozessnummer und die fremde bleibt unangetastet."""
    src = _f(tmp_path / "v" / "herbst.mp4")
    out = video.cache_path(src, tmp_path / "c", 1080, 1920, 24)
    fremd = _f(out.with_name(f"{out.stem}.99999.tmp.mp4"))       # Zwischendatei eines anderen Prozesses
    seen = {}

    def run(cmd, **kw):
        seen["tmp"] = cmd[-1]
        _f(__import__("pathlib").Path(cmd[-1]))
        class R: returncode = 0
        return R()

    monkeypatch.setattr(video.subprocess, "run", run)
    monkeypatch.setattr(video, "duration", lambda p: 10.0)
    monkeypatch.setattr(video.os, "getpid", lambda: 4242)
    video.prepare(src, tmp_path / "c", 1080, 1920, 24)
    assert seen["tmp"].endswith(".4242.tmp.mp4")
    assert fremd.exists(), "Zwischendatei des anderen Prozesses nicht überschrieben/gelöscht"
