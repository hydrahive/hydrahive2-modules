"""S8: Licht-Einstellungen – eine Prüfung für Dienst (normalize) und Server (light_ok), wie dash_layout."""
from __future__ import annotations

import copy

import pytest

from renderer import light_config as lc


def test_vorgaben_sind_gueltig_und_vollstaendig() -> None:
    d = lc.normalize(None)
    assert lc.light_ok(d)
    assert d["enabled"] is True and d["brightness"] == 80 and d["night_off"] is True
    assert set(d["states"]) == set(lc.STATES) == {"error", "warning", "done", "working"}
    assert d["states"]["error"]["color"] == "FF0000" and d["states"]["working"]["effect"] == "breathing"
    assert d["states"]["done"]["enabled"] is False and d["states"]["done"]["seconds"] == 5
    assert d["error_blink_seconds"] == 20
    assert set(d["seasons"]) == {"spring", "summer", "autumn", "winter"} and d["seasons_enabled"] is True


@pytest.mark.parametrize("raw, want", [("#ff8800", "FF8800"), ("00aaFF", "00AAFF"), ("FFFFFF", "FFFFFF")])
def test_farbe_wird_vereinheitlicht(raw, want) -> None:
    assert lc.color(raw) == want


@pytest.mark.parametrize("raw", ["", "FFF", "GG0000", "FF00001", "#12345", None, 123, "red", "FF 000"])
def test_falsche_farbe(raw) -> None:
    assert lc.color(raw) is None


def test_normalize_ersetzt_kaputtes_durch_vorgabe_und_behaelt_gutes() -> None:
    raw = {"enabled": "ja", "brightness": 150, "night_off": False, "error_blink_seconds": 30,
           "states": {"error": {"effect": "kaputt", "color": "#00ff00", "speed": 40},
                      "working": {"brightness": -5}, "nichtda": {}},
           "seasons": {"winter": {"color": "zz"}}, "fremd": 1}
    d = lc.normalize(raw)
    assert lc.light_ok(d)
    assert d["enabled"] is True and d["brightness"] == 80                      # kaputt → Vorgabe
    assert d["night_off"] is False and d["error_blink_seconds"] == 30          # gültig → bleibt
    assert d["states"]["error"]["effect"] == "flashing" and d["states"]["error"]["color"] == "00FF00"
    assert d["states"]["error"]["speed"] == 40
    assert d["states"]["working"]["brightness"] is None
    assert "nichtda" not in d["states"] and "fremd" not in d
    assert d["seasons"]["winter"]["color"] == lc.DEFAULTS["seasons"]["winter"]["color"]


def _ok(**patch) -> bool:
    d = copy.deepcopy(lc.DEFAULTS)
    for k, v in patch.items():
        d[k] = v
    return lc.light_ok(d)


@pytest.mark.parametrize("key, bad", [
    ("enabled", "ja"), ("brightness", 101), ("brightness", -1), ("brightness", True), ("night_off", 1),
    ("error_blink_seconds", 601), ("seasons_enabled", None), ("rest_color", "nope"), ("rest_effect", "wave"),
])
def test_server_lehnt_falsche_werte_ab(key, bad) -> None:
    assert not _ok(**{key: bad})


def test_server_lehnt_falschen_zustand_ab() -> None:
    d = copy.deepcopy(lc.DEFAULTS)
    d["states"]["working"]["effect"] = "rainbow"
    assert not lc.light_ok(d)
    d = copy.deepcopy(lc.DEFAULTS)
    d["states"]["done"]["seconds"] = 61
    assert not lc.light_ok(d)
    d = copy.deepcopy(lc.DEFAULTS)
    d["states"]["error"]["speed"] = 101
    assert not lc.light_ok(d)
    d = copy.deepcopy(lc.DEFAULTS)
    d["states"]["extra"] = {}
    assert not lc.light_ok(d)
    d = copy.deepcopy(lc.DEFAULTS)
    d["seasons"]["winter"]["effect"] = "rainbow"
    assert not lc.light_ok(d)


def test_unbekannter_schluessel_wird_abgelehnt() -> None:
    assert not _ok(fremd=1)


def test_effekte_fest() -> None:
    assert lc.EFFECTS == ("static", "breathing", "flashing", "off")
