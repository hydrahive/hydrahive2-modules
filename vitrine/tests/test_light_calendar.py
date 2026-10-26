"""S8: Licht aus dem Kalender – Anlass (Regel mit Lichtfarbe, auch ohne Video) und Jahreszeit."""
from __future__ import annotations

import datetime as dt

import pytest

from renderer import light_calendar as lcal
from renderer import light_config as lc


def _rule(name, frm, to, *, color="FF8800", effect="static", prio=50, enabled=True, videos=()):
    r = {"name": name, "kind": "range", "from": frm, "to": to, "priority": prio, "enabled": enabled,
         "videos": list(videos)}
    if color is not None:
        r["light_color"] = color
    if effect is not None:
        r["light_effect"] = effect
    return r


def test_regel_mit_lichtfarbe_auch_ohne_video() -> None:
    cfg = {"rules": [_rule("Halloween", "10-31", "10-31")]}
    got = lcal.occasion(cfg, dt.datetime(2026, 10, 31, 20, 0))
    assert got == ("Halloween", "static", "FF8800")
    assert lcal.occasion(cfg, dt.datetime(2026, 11, 1, 20, 0)) is None


def test_regel_ohne_lichtfarbe_zaehlt_nicht() -> None:
    cfg = {"rules": [_rule("Herbst", "09-01", "11-30", color=None, prio=10)]}
    assert lcal.occasion(cfg, dt.datetime(2026, 10, 31)) is None


def test_ausgeschaltete_regel_zaehlt_nicht() -> None:
    cfg = {"rules": [_rule("Halloween", "10-31", "10-31", enabled=False)]}
    assert lcal.occasion(cfg, dt.datetime(2026, 10, 31)) is None


def test_hoechste_prioritaet_gewinnt_bei_gleicher_die_erste() -> None:
    cfg = {"rules": [_rule("Advent", "12-01", "12-23", color="FFC040", prio=40),
                     _rule("Nikolaus", "12-06", "12-06", color="FF0000", prio=50),
                     _rule("Auch50", "12-06", "12-06", color="00FF00", prio=50)]}
    assert lcal.occasion(cfg, dt.datetime(2026, 12, 6))[0] == "Nikolaus"
    assert lcal.occasion(cfg, dt.datetime(2026, 12, 7))[0] == "Advent"


def test_kaputte_lichtfarbe_zaehlt_nicht_effekt_fehlt_static() -> None:
    cfg = {"rules": [_rule("A", "01-01", "01-01", color="nein"), _rule("B", "01-01", "01-01", effect=None, prio=10)]}
    assert lcal.occasion(cfg, dt.datetime(2027, 1, 1)) == ("B", "static", "FF8800")


@pytest.mark.parametrize("day, season", [((3, 1), "spring"), ((5, 31), "spring"), ((6, 1), "summer"),
                                         ((9, 1), "autumn"), ((11, 30), "autumn"), ((12, 1), "winter"),
                                         ((2, 28), "winter")])
def test_jahreszeit(day, season) -> None:
    assert lcal.season(dt.datetime(2026, day[0], day[1])) == season


def test_ruhe_jahreszeit_oder_feste_farbe() -> None:
    light = lc.normalize({})
    assert lcal.rest(light, dt.datetime(2026, 10, 26)) == ("autumn", "static", light["seasons"]["autumn"]["color"])
    light["seasons_enabled"] = False
    assert lcal.rest(light, dt.datetime(2026, 10, 26)) == ("rest", "static", light["rest_color"])


def test_vorlagen_haben_lichtfarben_und_sind_gueltig() -> None:
    """Vorschläge für die Vorlagen (SPEC-LICHT); gültig nach light_config und vom Schema akzeptiert."""
    from renderer import calendar
    by = {t["name"]: t for t in calendar.TEMPLATES}
    assert by["Halloween"]["light_color"] == "FF6A00"
    assert by["Weihnachten"]["light_color"] == "FF1A1A" and by["Advent"]["light_color"] == "FFB347"
    assert by["Silvester"]["light_effect"] == "flashing"
    for t in calendar.TEMPLATES:
        if "light_color" in t:
            assert lc.color(t["light_color"]) == t["light_color"] and t["light_effect"] in lc.EFFECTS, t["name"]
    assert "light_color" not in by["Herbst"], "Jahreszeiten kommen aus den Licht-Einstellungen, nicht aus Regeln"
