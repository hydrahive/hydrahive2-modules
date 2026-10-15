"""config.json laden (robust) und Nachtmodus."""
from __future__ import annotations

import datetime as dt
import json


from renderer import config as cfg
from renderer import night


def test_ohne_datei_standardwerte(tmp_path):
    c = cfg.load(tmp_path)
    assert c["rules"] == [] and c["default_videos"] == []
    assert c["night"] == {"enabled": False, "from": "23:00", "to": "07:00", "mode": "dim"}
    assert c["rotate_minutes"] == 10


def test_kaputte_datei_heisst_standardwerte(tmp_path):
    (tmp_path / "config.json").write_text("{kaputt")
    assert cfg.load(tmp_path)["rules"] == []


def test_teilweise_datei_wird_ergaenzt(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"night": {"enabled": True}, "rotate_minutes": 3}))
    c = cfg.load(tmp_path)
    assert c["night"]["enabled"] is True and c["night"]["from"] == "23:00" and c["rotate_minutes"] == 3


def test_falsche_typen_werden_ersetzt(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"rules": "x", "night": [], "rotate_minutes": "viel"}))
    c = cfg.load(tmp_path)
    assert c["rules"] == [] and c["night"]["enabled"] is False and c["rotate_minutes"] == 10


def test_speichern_atomar_und_lesbar(tmp_path):
    cfg.save(tmp_path, {**cfg.DEFAULTS, "rotate_minutes": 7})
    assert cfg.load(tmp_path)["rotate_minutes"] == 7
    assert not list(tmp_path.glob("*.tmp"))


def test_beobachter_meldet_nur_aenderungen(tmp_path):
    w = cfg.Watcher(tmp_path)
    first = w.poll()
    assert first is not None and w.poll() is None
    cfg.save(tmp_path, {**cfg.DEFAULTS, "rotate_minutes": 5})
    w._mtime = -1                      # Dateisystem-Zeitauflösung im Test umgehen
    assert w.poll()["rotate_minutes"] == 5


def test_nachtfenster():
    n = {"enabled": True, "from": "23:00", "to": "07:00", "mode": "dim"}
    assert night.active(n, dt.datetime(2026, 1, 1, 23, 0)) and night.active(n, dt.datetime(2026, 1, 2, 6, 59))
    assert not night.active(n, dt.datetime(2026, 1, 2, 7, 0)) and not night.active(n, dt.datetime(2026, 1, 1, 22, 59))
    assert not night.active({**n, "enabled": False}, dt.datetime(2026, 1, 1, 23, 30))
    assert night.active({**n, "from": "13:00", "to": "14:00"}, dt.datetime(2026, 1, 1, 13, 30))


def test_nachtbild_dim_hat_gedimmte_uhr_aus_ist_schwarz():
    t = dt.datetime(2026, 10, 15, 23, 41)
    dim = night.frame("dim", 1080, 1920, t)
    off = night.frame("off", 1080, 1920, t)
    assert dim.size == off.size == (1080, 1920)
    assert off.getbbox() is None, "aus = komplett schwarz"
    box = dim.getbbox()
    assert box is not None, "dim zeigt eine Uhr"
    assert max(hi for _, hi in dim.crop(box).getextrema()) <= 90, "Uhr bleibt dunkel (Wohnzimmer nachts)"
