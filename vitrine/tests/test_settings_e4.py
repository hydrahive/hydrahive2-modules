"""E4: Bildrate und Standard-Dauer der Einblendungen aus config.json (Cockpit stellt sie ein)."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from renderer import config as cfg
from renderer import inbox, program


def _write(tmp_path, **kw):
    (tmp_path / "config.json").write_text(json.dumps(kw))


def test_standardwerte(tmp_path):
    c = cfg.load(tmp_path)
    assert c["fps"] == 24 and c["message_seconds"] == 15


@pytest.mark.parametrize(("fps", "erwartet"), [(12, 12), (30, 30), (11, 24), (31, 24), ("24", 24), (None, 24), (True, 24)])
def test_bildrate_grenzen(tmp_path, fps, erwartet):
    _write(tmp_path, fps=fps)
    assert cfg.load(tmp_path)["fps"] == erwartet


@pytest.mark.parametrize(("sec", "erwartet"), [(5, 5), (120, 120), (4, 15), (121, 15), (False, 15), (7.5, 15)])
def test_einblenddauer_grenzen(tmp_path, sec, erwartet):
    _write(tmp_path, message_seconds=sec)
    assert cfg.load(tmp_path)["message_seconds"] == erwartet


def test_bildrate_gehoert_zum_programm(tmp_path):
    """Neue Bildrate → neuer Programmschlüssel → Dienst baut die Bildquelle neu (und den passenden Bildcache)."""
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "a.mp4").write_bytes(b"A")
    now = dt.datetime(2026, 10, 16, 12)
    p24 = program.current(tmp_path, {**cfg.DEFAULTS, "fps": 24}, now)
    p12 = program.current(tmp_path, {**cfg.DEFAULTS, "fps": 12}, now)
    assert p24.fps == 24 and p12.fps == 12 and p24.key() != p12.key()


def test_nachtprogramm_unabhaengig_von_bildrate():
    """Nachts 1 Bild/s – die Bildrate darf dann keinen Programmwechsel auslösen."""
    assert program.Program(night="dim", fps=24).key() == program.Program(night="dim", fps=12).key()
    assert program.Program(fps=24).key() != program.Program(fps=12).key()


def test_einblendung_nutzt_eingestellte_dauer(tmp_path):
    _write(tmp_path, message_seconds=40)
    m = inbox.post(tmp_path, "Hallo", now=1000.0)
    assert m["expires"] - m["created"] == 40


def test_fehler_bleiben_laenger(tmp_path):
    _write(tmp_path, message_seconds=40)
    m = inbox.post(tmp_path, "kaputt", kind="error", now=1000.0)
    assert m["expires"] - m["created"] == inbox.ERROR_SECONDS


def test_ausdrueckliche_dauer_gewinnt(tmp_path):
    _write(tmp_path, message_seconds=40)
    m = inbox.post(tmp_path, "kurz", seconds=8, now=1000.0)
    assert m["expires"] - m["created"] == 8


def test_dienst_nutzt_bildrate_aus_config(tmp_path):
    pytest.importorskip("usb")                     # Dienst-Teil braucht pyusb (Dienst-venv, nicht der Kern)
    from PIL import Image

    from renderer import main
    from test_main import FakeDisplay
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "a.mp4").write_bytes(b"A")
    _write(tmp_path, fps=12)
    seen, sleeps = [], []

    def frames(src, w, h, fps):
        seen.append(fps)
        while True:
            yield Image.new("RGB", (w, h))

    r = main.Runner(data_dir=tmp_path, connect=lambda: FakeDisplay(), frames=frames, status=lambda: "",
                    sleep=sleeps.append, now=lambda: dt.datetime(2026, 10, 16, 12), check_every=99)
    r.run(max_frames=3)
    assert seen == [12]
    assert sleeps and max(sleeps) > 1 / 24, "Takt passt zu 12 fps"


def test_grenzen_backend_und_dienst_gleich():
    """Was das Cockpit speichern darf, muss der Dienst auch annehmen (sonst stillschweigend Standardwert)."""
    import pytest as _pt
    _pt.importorskip("hydrahive")
    from backend.schemas import Config
    f = Config.model_fields
    def bounds(name):
        ge = next(m.ge for m in f[name].metadata if getattr(m, "ge", None) is not None)
        le = next(m.le for m in f[name].metadata if getattr(m, "le", None) is not None)
        return ge, le
    assert bounds("fps") == cfg.FPS_RANGE and bounds("message_seconds") == cfg.MESSAGE_RANGE
    assert f["fps"].default == cfg.DEFAULTS["fps"] and f["message_seconds"].default == cfg.DEFAULTS["message_seconds"]
