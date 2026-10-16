"""Vorschau auf dem Display: 30 s das Programm eines anderen Zeitpunkts, danach automatisch zurück."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from renderer import config as cfg
from renderer import preview, program

NOW = dt.datetime(2026, 10, 16, 10, 45)


@pytest.fixture
def data(tmp_path):
    (tmp_path / "videos").mkdir()
    for n in ("herbst.mp4", "weihnachten.mp4"):
        (tmp_path / "videos" / n).write_bytes(b"V")
    rules = [{"id": "h", "name": "Herbst", "kind": "season", "season": "autumn", "priority": 10, "enabled": True,
              "videos": ["herbst.mp4"]},
             {"id": "w", "name": "Weihnachten", "kind": "range", "from": "12-24", "to": "12-26", "priority": 50,
              "enabled": True, "videos": ["weihnachten.mp4"]}]
    cfg.save(tmp_path, {**cfg.DEFAULTS, "rules": rules})
    return tmp_path


def _prog(data, now=NOW, t=1000.0):
    return preview.current(data, cfg.load(data), now, t=t)


def test_ohne_vorschau_normales_programm(data):
    p = _prog(data)
    assert p.video.name == "herbst.mp4" and p.preview is None


def test_vorschau_zeigt_programm_des_zeitpunkts(data):
    preview.start(data, dt.datetime(2026, 12, 24, 19, 0), t=1000.0)
    p = _prog(data, t=1010.0)
    assert p.video.name == "weihnachten.mp4" and p.rule == "Weihnachten"
    assert p.preview == "Vorschau 24.12. 19:00"


def test_vorschau_endet_nach_30_sekunden(data):
    preview.start(data, dt.datetime(2026, 12, 24, 19, 0), t=1000.0)
    assert _prog(data, t=1000.0 + preview.SECONDS - 0.1).preview is not None
    p = _prog(data, t=1000.0 + preview.SECONDS + 0.1)
    assert p.preview is None and p.video.name == "herbst.mp4"
    assert not (data / "preview.json").exists(), "abgelaufene Datei wird aufgeräumt"


def test_dauer_ist_30_sekunden():
    assert preview.SECONDS == 30


def test_beenden(data):
    preview.start(data, dt.datetime(2026, 12, 24, 19, 0), t=1000.0)
    assert preview.stop(data) is True
    assert _prog(data, t=1001.0).preview is None
    assert preview.stop(data) is False


def test_neue_vorschau_ersetzt_alte(data):
    preview.start(data, dt.datetime(2026, 12, 24, 19, 0), t=1000.0)
    preview.start(data, dt.datetime(2026, 10, 31, 20, 0), t=1020.0)
    p = _prog(data, t=1045.0)
    assert p.preview == "Vorschau 31.10. 20:00" and p.video.name == "herbst.mp4"


def test_vorschau_gehoert_zum_programmschluessel(data):
    """Start und Ende der Vorschau müssen den Dienst umschalten lassen – auch wenn das Video gleich bleibt."""
    normal = _prog(data)
    preview.start(data, dt.datetime(2026, 10, 31, 20, 0), t=1000.0)
    vor = _prog(data, t=1001.0)
    assert vor.video == normal.video and vor.key() != normal.key()


def test_nachtmodus_in_der_vorschau(data):
    cfg.save(data, {**cfg.load(data), "night": {"enabled": True, "from": "23:00", "to": "07:00", "mode": "dim"}})
    preview.start(data, dt.datetime(2026, 12, 24, 2, 0), t=1000.0)
    p = _prog(data, t=1001.0)
    assert p.night == "dim" and p.preview == "Vorschau 24.12. 02:00"


@pytest.mark.parametrize("inhalt", ["{kaputt", "[]", json.dumps({"at": "gestern", "until": 2000}),
                                    json.dumps({"at": "2026-12-24T19:00"}), json.dumps({"until": 2000})])
def test_kaputte_datei_heisst_normales_programm(data, inhalt):
    (data / "preview.json").write_text(inhalt)
    p = _prog(data, t=1000.0)
    assert p.preview is None and p.video.name == "herbst.mp4"


def test_datei_atomar_und_lesbar(data):
    preview.start(data, dt.datetime(2026, 12, 24, 19, 0), t=1000.0)
    raw = json.loads((data / "preview.json").read_text())
    assert raw == {"at": "2026-12-24T19:00:00", "until": 1030.0}
    assert not list(data.glob("*.tmp"))


def test_normales_programm_hat_kein_vorschaufeld():
    assert program.Program().preview is None
    assert program.Program().key() == program.Program().key()


def test_zeile_unter_dem_datum():
    assert preview.headline(program.Program(holiday="Weihnachten")) == "Weihnachten"
    assert preview.headline(program.Program()) is None
    assert preview.headline(program.Program(preview="Vorschau 24.12. 19:00")) == "Vorschau 24.12. 19:00"
    assert preview.headline(program.Program(preview="Vorschau 24.12. 19:00", holiday="Weihnachten")) == \
        "Vorschau 24.12. 19:00 · Weihnachten"


def test_dienst_nutzt_die_vorschau(data, monkeypatch):
    pytest.importorskip("usb")
    from PIL import Image

    from renderer import main, scene
    from test_main import FakeDisplay
    seen_src, seen_line = [], []
    orig = scene.Overlay.render

    def spy(self, t, status, holiday=None, alert=False):
        seen_line.append(holiday)
        return orig(self, t, status, holiday, alert)

    monkeypatch.setattr(scene.Overlay, "render", spy)

    def frames(src, w, h, fps):
        seen_src.append(src.name)
        while True:
            yield Image.new("RGB", (w, h))

    preview.start(data, dt.datetime(2026, 12, 24, 19, 0))
    r = main.Runner(data_dir=data, connect=lambda: FakeDisplay(), frames=frames, status=lambda: "",
                    sleep=lambda s: None, now=lambda: NOW, check_every=99)
    r.run(max_frames=2)
    assert seen_src == ["weihnachten.mp4"]
    assert set(seen_line) == {"Vorschau 24.12. 19:00 · Weihnachten"}
    st = json.loads((data / "state.json").read_text())
    assert st["preview"] == "Vorschau 24.12. 19:00" and st["rule"] == "Weihnachten"
