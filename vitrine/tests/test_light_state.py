"""S8: Welcher Lichtzustand gilt? Nacht > Fehler > Wartet > Fertig > Arbeitet > Anlass > Jahreszeit."""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

import pytest

from renderer import inbox
from renderer import light_config as lc
from renderer import light_state as ls

NOW = dt.datetime(2026, 10, 26, 15, 0)       # Herbst, kein Anlass
T = NOW.timestamp()


@pytest.fixture
def data(tmp_path: Path) -> Path:
    return tmp_path


def _cfg(**light) -> dict:
    return {"rules": [], "night": {"enabled": False, "from": "23:00", "to": "07:00", "mode": "dim"},
            "light": lc.normalize(light)}


def _hydra(data: Path, agents: int, *, age: float = 0.0) -> None:
    (data / "hydra.json").write_text(json.dumps({"agents": agents, "errors_last_hour": 0, "updated": T - age}))


def _pick(data: Path, cfg: dict, *, now=NOW, mem: ls.Memory | None = None) -> ls.Look | None:
    return ls.choose(data, cfg, now, mem or ls.Memory())


def test_ruhe_ist_jahreszeit(data) -> None:
    look = _pick(data, _cfg())
    assert look.state == "autumn" and look.effect == "static"
    assert look.color == lc.DEFAULTS["seasons"]["autumn"]["color"] and look.brightness == 80


def test_licht_aus_gibt_none(data) -> None:
    assert _pick(data, _cfg(enabled=False)) is None


def test_nacht_aus(data) -> None:
    cfg = _cfg()
    cfg["night"] = {"enabled": True, "from": "14:00", "to": "16:00", "mode": "dim"}
    look = _pick(data, cfg)
    assert look.state == "night" and look.effect == "off"
    cfg["light"]["night_off"] = False
    assert _pick(data, cfg).state == "autumn"


def test_arbeitet(data) -> None:
    _hydra(data, 2)
    look = _pick(data, _cfg())
    assert look.state == "working" and look.effect == "breathing" and look.speed == 30


def test_hydra_json_alt_heisst_nicht_arbeitet(data) -> None:
    _hydra(data, 2, age=200)
    assert _pick(data, _cfg()).state == "autumn"


def test_wartet_schlaegt_arbeitet(data) -> None:
    _hydra(data, 1)
    inbox.post(data, "Bitte prüfen", kind="warning", now=T - 10)
    assert _pick(data, _cfg()).state == "warning"


def test_info_aendert_nichts(data) -> None:
    inbox.post(data, "Nur Info", kind="info", now=T - 1)
    inbox.post(data, "Klappt", kind="success", now=T - 1)
    assert _pick(data, _cfg()).state == "autumn"


def test_fehler_blinkt_zuerst_dann_stehend(data) -> None:
    inbox.post(data, "Kaputt", kind="error", now=T - 5)
    look = _pick(data, _cfg())
    assert look.state == "error" and look.effect == "flashing" and look.color == "FF0000"
    inbox.post(data, "Kaputt", kind="error", now=T - 5)       # gleiche Meldung → zählt nur hoch
    later = _pick(data, _cfg(), now=NOW + dt.timedelta(seconds=30))
    assert later.state == "error" and later.effect == "static"


def test_fehler_ohne_blinkzeit_sofort_stehend(data) -> None:
    inbox.post(data, "Kaputt", kind="error", now=T - 1)
    assert _pick(data, _cfg(error_blink_seconds=0)).effect == "static"


def test_fehler_schlaegt_wartet_und_nacht_schlaegt_fehler(data) -> None:
    inbox.post(data, "Achtung", kind="warning", now=T - 1)
    inbox.post(data, "Kaputt", kind="error", now=T - 1)
    cfg = _cfg()
    assert _pick(data, cfg).state == "error"
    cfg["night"] = {"enabled": True, "from": "14:00", "to": "16:00", "mode": "off"}
    assert _pick(data, cfg).state == "night"


def test_gelesener_fehler_zaehlt_nicht(data) -> None:
    m = inbox.post(data, "Kaputt", kind="error", now=T - 1)
    inbox.mark_read(data, m["id"], now=T)
    assert _pick(data, _cfg()).state == "autumn"


def test_fertig_nur_wenn_eingeschaltet_und_nur_fuer_die_dauer(data) -> None:
    on = {"states": {"done": {"enabled": True, "seconds": 5}}}
    mem = ls.Memory()
    _hydra(data, 1)
    assert _pick(data, _cfg(**on), mem=mem).state == "working"
    _hydra(data, 0)
    assert _pick(data, _cfg(**on), mem=mem).state == "done"
    assert _pick(data, _cfg(**on), now=NOW + dt.timedelta(seconds=4), mem=mem).state == "done"
    assert _pick(data, _cfg(**on), now=NOW + dt.timedelta(seconds=6), mem=mem).state == "autumn"
    mem2 = ls.Memory()
    _hydra(data, 1)
    _pick(data, _cfg(), mem=mem2)
    _hydra(data, 0)
    assert _pick(data, _cfg(), mem=mem2).state == "autumn"         # Vorgabe: aus


def test_anlass_aus_dem_kalender(data) -> None:
    cfg = _cfg()
    cfg["rules"] = [{"name": "Halloween", "kind": "range", "from": "10-31", "to": "10-31", "priority": 50,
                     "light_color": "FF6A00", "light_effect": "breathing", "videos": []}]
    look = _pick(data, cfg, now=dt.datetime(2026, 10, 31, 20, 0))
    assert look.state == "occasion" and look.label == "Halloween" and look.color == "FF6A00"
    assert look.effect == "breathing"


def test_eigene_helligkeit_je_zustand(data) -> None:
    _hydra(data, 1)
    assert _pick(data, _cfg(states={"working": {"brightness": 40}})).brightness == 40


def test_effekt_aus_heisst_schwarz(data) -> None:
    _hydra(data, 1)
    look = _pick(data, _cfg(states={"working": {"effect": "off"}}))
    assert look.state == "working" and look.effect == "off"


def test_schluessel_fuer_aenderung() -> None:
    a = ls.Look("working", "breathing", "0060FF", 80, 30)
    assert a.key() == ls.Look("working", "breathing", "0060FF", 80, 30, label="x").key()
    assert a.key() != ls.Look("working", "breathing", "0060FF", 70, 30).key()


def test_kaputte_dateien_stoppen_nichts(data) -> None:
    (data / "hydra.json").write_text("{kaputt")
    (data / "inbox").mkdir()
    (data / "inbox" / "x.json").write_text("nein")
    assert _pick(data, _cfg()).state == "autumn"
    assert time.time() > 0
