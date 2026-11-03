"""Programm: was das Display gerade zeigen soll (Video nach Kalender, Nachtmodus, Feiertagsname)."""
from __future__ import annotations

import datetime as dt

import pytest

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


def _night_video_cfg(**pools):
    return {
        **CFG,
        "night": {
            "enabled": True,
            "from": "23:00",
            "to": "07:00",
            "mode": "video",
            "videos": {
                "spring": pools.get("spring", []),
                "summer": pools.get("summer", []),
                "autumn": pools.get("autumn", []),
                "winter": pools.get("winter", []),
            },
        },
    }


@pytest.mark.parametrize(("when", "_season", "name"), [
    (dt.datetime(2026, 3, 1, 23, 30), "spring", "fruehling.mp4"),
    (dt.datetime(2026, 6, 1, 23, 30), "summer", "sommer.mp4"),
    (dt.datetime(2026, 9, 1, 23, 30), "autumn", "herbst.mp4"),
    (dt.datetime(2026, 12, 1, 23, 30), "winter", "winter.mp4"),
    (dt.datetime(2026, 2, 28, 23, 30), "winter", "winter.mp4"),
])
def test_nachtvideo_waehlt_pool_der_meteorologischen_saison(tmp_path, when, _season, name):
    names = ["fruehling.mp4", "sommer.mp4", "herbst.mp4", "winter.mp4"]
    data = _vids(tmp_path, *names)
    config = _night_video_cfg(
        spring=[names[0]], summer=[names[1]], autumn=[names[2]], winter=[names[3]],
    )

    p = program.current(data, config, when)

    assert p.night == "video"
    assert p.video == data / "videos" / name
    assert p.rule is None


def test_nachtvideo_filtert_fehlende_dateien_und_rotiert(tmp_path):
    data = _vids(tmp_path, "sommer-1.mp4", "sommer-2.mp4")
    config = _night_video_cfg(summer=["fehlt.mp4", "sommer-1.mp4", "sommer-2.mp4"])
    config["rotate_minutes"] = 10
    first = dt.datetime(2026, 6, 1, 23, 0)

    a = program.current(data, config, first)
    b = program.current(data, config, first + dt.timedelta(minutes=10))

    assert {a.video.name, b.video.name} == {"sommer-1.mp4", "sommer-2.mp4"}


def test_nachtvideo_ohne_vorhandene_saison_datei_faellt_auf_dim(tmp_path):
    data = _vids(tmp_path, "tag.mp4")
    config = _night_video_cfg(winter=["fehlt.mp4"])

    p = program.current(data, config, dt.datetime(2026, 12, 1, 23, 30))

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


def test_regelwechsel_bei_gleichem_video_aendert_den_schluessel(tmp_path):
    """Gleiches Video, aber jetzt über eine Regel gewählt → Status muss die Regel zeigen (live gefunden 15.10.)."""
    data = _vids(tmp_path, "herbst.mp4")
    ohne = program.current(data, {"rules": []}, dt.datetime(2026, 10, 15, 12))
    mit = program.current(data, CFG, dt.datetime(2026, 10, 15, 12))
    assert ohne.video == mit.video and ohne.rule is None and mit.rule == "Herbst"
    assert ohne.key() != mit.key()
