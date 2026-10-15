"""Programm: was das Display gerade zeigen soll (Video nach Kalender, Nachtmodus, Feiertagsname)."""
from __future__ import annotations

import datetime as dt

from renderer import program


def _vids(tmp_path, *names):
    d = tmp_path / "videos"
    d.mkdir(exist_ok=True)
    for n in names:
        (d / n).write_bytes(b"x")
    return tmp_path


CFG = {
    "rules": [
        {"id": "1", "name": "Weihnachten", "kind": "range", "from": "12-24", "to": "12-26", "priority": 60, "enabled": True, "videos": ["weihnachten.mp4"]},
        {"id": "2", "name": "Herbst", "kind": "season", "season": "autumn", "priority": 10, "enabled": True, "videos": ["herbst.mp4"]},
    ],
    "default_videos": [],
    "night": {"enabled": True, "from": "23:00", "to": "07:00", "mode": "dim"},
    "rotate_minutes": 10,
}


def test_regel_bestimmt_video(tmp_path):
    data = _vids(tmp_path, "herbst.mp4", "weihnachten.mp4")
    p = program.current(data, CFG, dt.datetime(2026, 10, 15, 19))
    assert p.video == data / "videos" / "herbst.mp4" and p.rule == "Herbst" and p.holiday is None and not p.night


def test_feiertag_mit_name(tmp_path):
    data = _vids(tmp_path, "herbst.mp4", "weihnachten.mp4")
    p = program.current(data, CFG, dt.datetime(2026, 12, 24, 18))
    assert p.video.name == "weihnachten.mp4" and p.holiday == "Weihnachten"


def test_nacht_vor_allem(tmp_path):
    data = _vids(tmp_path, "weihnachten.mp4")
    p = program.current(data, CFG, dt.datetime(2026, 12, 24, 23, 30))
    assert p.night == "dim" and p.video is None


def test_ohne_videos_kein_video(tmp_path):
    p = program.current(tmp_path, CFG, dt.datetime(2026, 10, 15, 12))
    assert p.video is None and not p.night


def test_versteckte_und_fremde_dateien_zaehlen_nicht(tmp_path):
    data = _vids(tmp_path, ".herbst.mp4", "notiz.txt")
    assert program.available(data) == set()


def test_gleiches_programm_gleich(tmp_path):
    data = _vids(tmp_path, "herbst.mp4", "weihnachten.mp4")
    a = program.current(data, CFG, dt.datetime(2026, 10, 15, 12, 0))
    b = program.current(data, CFG, dt.datetime(2026, 10, 15, 12, 3))
    assert a.key() == b.key()
    c = program.current(data, CFG, dt.datetime(2026, 12, 24, 12, 0))
    assert a.key() != c.key()


def test_ohne_feiertagsvideo_faellt_auf_vorhandene_zurueck(tmp_path):
    data = _vids(tmp_path, "herbst.mp4")
    p = program.current(data, CFG, dt.datetime(2026, 12, 24, 12))
    assert p.video.name == "herbst.mp4" and p.holiday is None and p.rule is None
