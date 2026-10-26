"""S8: Licht-Thread – nur bei Änderung setzen, alle 10 min neu, Vorschau, Status-Datei, Fehler stoppen nichts."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from renderer import config, light_preview, light_rgb
from renderer import light_runner as lr

NOW = dt.datetime(2026, 10, 26, 15, 0)


class FakeRGB:
    def __init__(self, device=light_rgb.Device(1, "B850 AORUS ELITE X3D"), fail: str | None = None):
        self.device, self.fail, self.applied, self.finds = device, fail, [], 0

    def find(self, cfg_dir):
        self.finds += 1
        return self.device

    def apply(self, look, device, cfg_dir):
        if self.fail:
            raise light_rgb.LightError(self.fail)
        self.applied.append(look.key())


@pytest.fixture
def data(tmp_path: Path) -> Path:
    config.save(tmp_path, {"light": {}})
    return tmp_path


def _hydra(data: Path, agents: int, t: float) -> None:
    (data / "hydra.json").write_text(json.dumps({"agents": agents, "updated": t}))


def _runner(data, fake, clock):
    return lr.LightRunner(data, find=fake.find, apply=fake.apply, now=lambda: clock[0])


def test_setzt_beim_start_und_dann_nur_bei_aenderung(data) -> None:
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    r.tick()
    assert len(fake.applied) == 1 and fake.applied[0][0] == "autumn"
    _hydra(data, 1, NOW.timestamp())
    r.tick()
    assert len(fake.applied) == 2 and fake.applied[1][0] == "working"
    st = json.loads((data / "light.json").read_text())
    assert st["device"] == "B850 AORUS ELITE X3D" and st["state"] == "working" and st["color"] == "0060FF"
    assert st["error"] is None and st["updated"] > 0


def test_alle_10_minuten_neu_auch_ohne_aenderung(data) -> None:
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    clock[0] = NOW + dt.timedelta(seconds=lr.REFRESH_SECONDS - 1)
    r.tick()
    assert len(fake.applied) == 1
    clock[0] = NOW + dt.timedelta(seconds=lr.REFRESH_SECONDS + 1)
    r.tick()
    assert len(fake.applied) == 2


def test_licht_aus_fasst_nichts_an(data) -> None:
    config.save(data, {"light": {"enabled": False}})
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    assert fake.applied == [] and fake.finds == 0
    assert json.loads((data / "light.json").read_text())["state"] == "disabled"


def test_einstellung_wirkt_beim_naechsten_durchlauf(data) -> None:
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    config.save(data, {"light": {"brightness": 40}})
    clock[0] = NOW + dt.timedelta(seconds=2)
    r.tick()
    assert fake.applied[-1][3] == 40


def test_kein_geraet_wartet_und_meldet(data) -> None:
    fake, clock = FakeRGB(device=None), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    r.tick()
    assert fake.finds == 1 and fake.applied == []
    st = json.loads((data / "light.json").read_text())
    assert st["device"] is None and "nicht gefunden" in st["error"]
    clock[0] = NOW + dt.timedelta(seconds=lr.SEARCH_SECONDS + 1)
    fake.device = light_rgb.Device(0, "Board")
    r.tick()
    assert fake.finds == 2 and len(fake.applied) == 1


def test_fehler_beim_setzen_wird_gemeldet_und_erneut_versucht(data) -> None:
    fake, clock = FakeRGB(fail="Error: kaputt"), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    assert json.loads((data / "light.json").read_text())["error"] == "Error: kaputt"
    fake.fail = None
    clock[0] = NOW + dt.timedelta(seconds=lr.RETRY_SECONDS + 1)
    r.tick()
    assert len(fake.applied) == 1
    assert json.loads((data / "light.json").read_text())["error"] is None


def test_vorschau_zeigt_zustand_und_dann_zurueck(data) -> None:
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    r.tick()
    light_preview.start(data, "error", t=NOW.timestamp())
    r.tick()
    assert fake.applied[-1][0] == "error"
    assert json.loads((data / "light.json").read_text())["preview"] == "error"
    clock[0] = NOW + dt.timedelta(seconds=light_preview.SECONDS + 1)
    r.tick()
    assert fake.applied[-1][0] == "autumn"


def test_vorschau_jahreszeit_und_nacht(data) -> None:
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    light_preview.start(data, "winter", t=NOW.timestamp())
    r.tick()
    assert fake.applied[-1][0] == "winter"
    light_preview.start(data, "night", t=NOW.timestamp())
    r.tick()
    assert fake.applied[-1][:2] == ("night", "off")


def test_vorschau_falscher_zustand_wird_abgelehnt(data) -> None:
    with pytest.raises(ValueError):
        light_preview.start(data, "../etc")


def test_ausnahme_im_durchlauf_stoppt_die_schleife_nicht(data, monkeypatch) -> None:
    fake, clock = FakeRGB(), [NOW]
    r = _runner(data, fake, clock)
    calls = []

    def boom():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("kaputt")
    monkeypatch.setattr(r, "tick", boom)
    r.loop(max_ticks=3, sleep=lambda s: None)
    assert len(calls) == 3


def test_start_ohne_openrgb_gibt_none(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(lr.shutil, "which", lambda name: None)
    assert lr.start(tmp_path) is None
