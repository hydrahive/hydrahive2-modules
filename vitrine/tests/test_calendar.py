"""Kalender-Regeln: welche Videos laufen wann (gleiche Logik für Dienst und Cockpit-Vorschau)."""
from __future__ import annotations

import datetime as dt

import pytest

from renderer import calendar as cal

VIDS = {"herbst.mp4", "winter.mp4", "weihnachten.mp4", "ostern.mp4", "abend.mp4", "standard.mp4", "silvester.mp4", "advent.mp4"}


def R(**kw):
    base = {"id": kw.get("name", "r"), "name": "r", "enabled": True, "priority": 10, "videos": []}
    return {**base, **kw}


@pytest.mark.parametrize(("year", "easter"), [(2026, dt.date(2026, 4, 5)), (2027, dt.date(2027, 3, 28)), (2028, dt.date(2028, 4, 16))])
def test_ostersonntag(year, easter):
    assert cal.easter(year) == easter


@pytest.mark.parametrize(("year", "first"), [(2026, dt.date(2026, 11, 29)), (2027, dt.date(2027, 11, 28)), (2023, dt.date(2023, 12, 3))])
def test_erster_advent(year, first):
    assert cal.first_advent(year) == first


def test_bereich_normal_und_ueber_jahreswechsel():
    weih = R(kind="range", **{"from": "12-24", "to": "12-26"})
    sil = R(kind="range", **{"from": "12-31", "to": "01-01"})
    assert cal.matches(weih, dt.datetime(2026, 12, 24, 0, 1))
    assert cal.matches(weih, dt.datetime(2026, 12, 26, 23, 59))
    assert not cal.matches(weih, dt.datetime(2026, 12, 27, 0, 0))
    assert cal.matches(sil, dt.datetime(2026, 12, 31, 20)) and cal.matches(sil, dt.datetime(2027, 1, 1, 10))
    assert not cal.matches(sil, dt.datetime(2027, 1, 2))


def test_ostern_relativ():
    karfreitag_bis_ostermontag = R(kind="easter", offset_from=-2, offset_to=1)
    assert cal.matches(karfreitag_bis_ostermontag, dt.datetime(2026, 4, 3, 9))
    assert cal.matches(karfreitag_bis_ostermontag, dt.datetime(2026, 4, 6, 22))
    assert not cal.matches(karfreitag_bis_ostermontag, dt.datetime(2026, 4, 7))
    pfingsten = R(kind="easter", offset_from=49, offset_to=50)
    assert cal.matches(pfingsten, dt.datetime(2026, 5, 24)) and not cal.matches(pfingsten, dt.datetime(2026, 5, 23))


def test_advent():
    adv = R(kind="advent")
    assert not cal.matches(adv, dt.datetime(2026, 11, 28, 23))
    assert cal.matches(adv, dt.datetime(2026, 11, 29, 0)) and cal.matches(adv, dt.datetime(2026, 12, 23, 23))
    assert not cal.matches(adv, dt.datetime(2026, 12, 24))


@pytest.mark.parametrize(("season", "inside", "outside"), [
    ("spring", dt.datetime(2026, 3, 1), dt.datetime(2026, 6, 1)),
    ("summer", dt.datetime(2026, 8, 31, 23), dt.datetime(2026, 9, 1)),
    ("autumn", dt.datetime(2026, 10, 15), dt.datetime(2026, 12, 1)),
    ("winter", dt.datetime(2027, 2, 28), dt.datetime(2027, 3, 1)),
    ("winter", dt.datetime(2026, 12, 1), dt.datetime(2026, 11, 30)),
])
def test_jahreszeiten(season, inside, outside):
    r = R(kind="season", season=season)
    assert cal.matches(r, inside) and not cal.matches(r, outside)


def test_tageszeit_auch_ueber_mitternacht():
    abend = R(kind="time", **{"from": "18:00", "to": "23:00"})
    nacht = R(kind="time", **{"from": "22:00", "to": "06:00"})
    assert cal.matches(abend, dt.datetime(2026, 1, 1, 18, 0)) and not cal.matches(abend, dt.datetime(2026, 1, 1, 23, 0))
    assert cal.matches(nacht, dt.datetime(2026, 1, 1, 23, 30)) and cal.matches(nacht, dt.datetime(2026, 1, 2, 5, 59))
    assert not cal.matches(nacht, dt.datetime(2026, 1, 2, 6, 0))


def test_hoechste_prioritaet_gewinnt():
    rules = [R(name="Herbst", kind="season", season="autumn", priority=10, videos=["herbst.mp4"]),
             R(name="Abend", kind="time", priority=20, videos=["abend.mp4"], **{"from": "18:00", "to": "23:00"})]
    c = cal.choose({"rules": rules}, dt.datetime(2026, 10, 15, 19), VIDS)
    assert c.videos == ["abend.mp4"] and c.rule == "Abend"
    c = cal.choose({"rules": rules}, dt.datetime(2026, 10, 15, 12), VIDS)
    assert c.videos == ["herbst.mp4"] and c.rule == "Herbst"


def test_gleichstand_legt_videos_zusammen_ohne_doppelte():
    rules = [R(name="A", kind="season", season="autumn", priority=10, videos=["herbst.mp4", "abend.mp4"]),
             R(name="B", kind="time", priority=10, videos=["abend.mp4", "standard.mp4"], **{"from": "00:00", "to": "23:59"})]
    c = cal.choose({"rules": rules}, dt.datetime(2026, 10, 15, 12), VIDS)
    assert c.videos == ["herbst.mp4", "abend.mp4", "standard.mp4"]


def test_regel_ohne_vorhandene_videos_und_ausgeschaltete_zaehlen_nicht():
    rules = [R(name="Weg", kind="season", season="autumn", priority=90, videos=["geloescht.mp4"]),
             R(name="Aus", kind="season", season="autumn", priority=80, videos=["abend.mp4"], enabled=False),
             R(name="Herbst", kind="season", season="autumn", priority=10, videos=["herbst.mp4"])]
    c = cal.choose({"rules": rules}, dt.datetime(2026, 10, 15), VIDS)
    assert c.rule == "Herbst"


def test_rueckfall_standard_dann_alle_dann_nichts():
    t = dt.datetime(2026, 7, 1)
    assert cal.choose({"rules": [], "default_videos": ["standard.mp4"]}, t, VIDS).videos == ["standard.mp4"]
    c = cal.choose({"rules": [], "default_videos": ["fehlt.mp4"]}, t, {"b.mp4", "a.mp4"})
    assert c.videos == ["a.mp4", "b.mp4"] and c.rule is None
    assert cal.choose({}, t, set()).videos == []


def test_feiertagsname_nur_bei_feiertagsregeln():
    rules = [R(name="Weihnachten", kind="range", priority=50, videos=["weihnachten.mp4"], **{"from": "12-24", "to": "12-26"}),
             R(name="Winter", kind="season", season="winter", priority=10, videos=["winter.mp4"])]
    assert cal.choose({"rules": rules}, dt.datetime(2026, 12, 24), VIDS).holiday == "Weihnachten"
    assert cal.choose({"rules": rules}, dt.datetime(2026, 12, 28), VIDS).holiday is None


def test_rotation_stabil_und_wechselnd():
    vids = ["a.mp4", "b.mp4", "c.mp4"]
    t = dt.datetime(2026, 10, 15, 12, 0)
    assert cal.rotate(vids, t, 10) == cal.rotate(vids, t + dt.timedelta(minutes=9), 10)
    assert cal.rotate(vids, t, 10) != cal.rotate(vids, t + dt.timedelta(minutes=10), 10)
    seen = {cal.rotate(vids, t + dt.timedelta(minutes=10 * i), 10) for i in range(3)}
    assert seen == set(vids)
    assert cal.rotate([], t, 10) is None and cal.rotate(["x.mp4"], t, 0) == "x.mp4"


def test_unbekannte_art_passt_nie():
    assert not cal.matches(R(kind="vollmond"), dt.datetime(2026, 1, 1))
    assert not cal.matches(R(kind="range", **{"from": "kaputt", "to": "12-01"}), dt.datetime(2026, 1, 1))


def test_vorlagen_sind_gueltig():
    for tpl in cal.TEMPLATES:
        assert tpl["kind"] in cal.KINDS and tpl["name"]
        assert cal.validate_rule({**tpl, "id": "x", "videos": [], "enabled": True}) == []
    names = {t["name"] for t in cal.TEMPLATES}
    assert {"Weihnachten", "Silvester", "Ostern", "Advent", "Halloween", "Frühling", "Sommer", "Herbst", "Winter"} <= names


@pytest.mark.parametrize(("rule", "fehler"), [
    ({"kind": "range", "from": "13-01", "to": "12-01"}, "from"),
    ({"kind": "range", "from": "02-30", "to": "03-01"}, "from"),
    ({"kind": "time", "from": "25:00", "to": "06:00"}, "from"),
    ({"kind": "season", "season": "monsun"}, "season"),
    ({"kind": "easter", "offset_from": 3, "offset_to": -1}, "offset"),
    ({"kind": "easter", "offset_from": -400, "offset_to": 0}, "offset"),
    ({"kind": "mond"}, "kind"),
])
def test_validierung(rule, fehler):
    errs = cal.validate_rule({"id": "x", "name": "n", "enabled": True, "priority": 10, "videos": [], **rule})
    assert errs and any(fehler in e for e in errs)


def test_29_februar_ist_gueltig():
    r = {"id": "x", "name": "Schalttag", "enabled": True, "priority": 10, "videos": [], "kind": "range", "from": "02-29", "to": "02-29"}
    assert cal.validate_rule(r) == []
    assert cal.matches(r, dt.datetime(2028, 2, 29))
