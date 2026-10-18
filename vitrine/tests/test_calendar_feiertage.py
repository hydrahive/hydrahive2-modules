"""Kalender-Erweiterung: einzelne Adventssonntage, n-ter Wochentag (Muttertag), Termine je Jahr (Chanukka/Ramadan)."""
from __future__ import annotations

import datetime as dt

import pytest

from renderer import calendar as cal


def R(**kw):
    return {"id": "r", "name": "r", "enabled": True, "priority": 10, "videos": [], **kw}


@pytest.mark.parametrize(("n", "erster", "letzter"), [
    (1, dt.date(2026, 11, 29), dt.date(2026, 12, 5)),
    (2, dt.date(2026, 12, 6), dt.date(2026, 12, 12)),
    (3, dt.date(2026, 12, 13), dt.date(2026, 12, 19)),
    (4, dt.date(2026, 12, 20), dt.date(2026, 12, 23)),
])
def test_adventssonntag_einzeln(n, erster, letzter):
    r = R(kind="advent_sunday", n=n)
    assert not cal.matches(r, dt.datetime.combine(erster - dt.timedelta(days=1), dt.time(23, 59)))
    assert cal.matches(r, dt.datetime.combine(erster, dt.time(0, 0)))
    assert cal.matches(r, dt.datetime.combine(letzter, dt.time(23, 59)))
    assert not cal.matches(r, dt.datetime.combine(letzter + dt.timedelta(days=1), dt.time(0, 0)))


def test_vierter_advent_am_24_dezember_ist_nur_ein_tag_heiligabend():
    # 2023: 4. Advent = 24.12. → Regel endet am 23.12., also kein Tag – Weihnachten übernimmt
    r = R(kind="advent_sunday", n=4)
    assert not any(cal.matches(r, dt.datetime(2023, 12, d, 12)) for d in range(17, 27))
    assert cal.matches(R(kind="advent_sunday", n=3), dt.datetime(2023, 12, 23, 12))


@pytest.mark.parametrize(("year", "muttertag"), [(2026, 10), (2027, 9), (2028, 14), (2029, 13)])
def test_muttertag_zweiter_sonntag_im_mai(year, muttertag):
    r = R(kind="nth_weekday", month=5, weekday=6, n=2)
    assert cal.matches(r, dt.datetime(year, 5, muttertag, 8))
    assert not cal.matches(r, dt.datetime(year, 5, muttertag - 1, 23))
    assert not cal.matches(r, dt.datetime(year, 5, muttertag + 1, 0))


def test_nter_wochentag_letzter_und_dauer():
    letzter_mo_mai = R(kind="nth_weekday", month=5, weekday=0, n=-1, days=2)
    assert cal.matches(letzter_mo_mai, dt.datetime(2026, 5, 25)) and cal.matches(letzter_mo_mai, dt.datetime(2026, 5, 26))
    assert not cal.matches(letzter_mo_mai, dt.datetime(2026, 5, 27)) and not cal.matches(letzter_mo_mai, dt.datetime(2026, 5, 18))
    fuenfter = R(kind="nth_weekday", month=2, weekday=6, n=5)          # Feb 2026 hat keinen 5. Sonntag
    assert not any(cal.matches(fuenfter, dt.datetime(2026, 2, d)) for d in range(1, 29))


def test_termine_je_jahr_auch_ueber_jahreswechsel():
    r = R(kind="dates", dates=[{"from": "2026-12-04", "to": "2026-12-12"}, {"from": "2027-12-24", "to": "2028-01-01"}])
    assert cal.matches(r, dt.datetime(2026, 12, 4, 18)) and cal.matches(r, dt.datetime(2026, 12, 12, 23))
    assert not cal.matches(r, dt.datetime(2026, 12, 13)) and not cal.matches(r, dt.datetime(2027, 12, 4))
    assert cal.matches(r, dt.datetime(2027, 12, 31)) and cal.matches(r, dt.datetime(2028, 1, 1, 12))
    assert not cal.matches(r, dt.datetime(2028, 1, 2))
    assert not cal.matches(R(kind="dates", dates=[]), dt.datetime(2026, 12, 5))


def test_neue_arten_sind_feiertage():
    for kind in ("advent_sunday", "nth_weekday", "dates"):
        assert kind in cal.KINDS and kind in cal.HOLIDAY_KINDS


@pytest.mark.parametrize(("rule", "fehler"), [
    ({"kind": "advent_sunday", "n": 5}, "n"),
    ({"kind": "advent_sunday"}, "n"),
    ({"kind": "nth_weekday", "month": 13, "weekday": 6, "n": 2}, "month"),
    ({"kind": "nth_weekday", "month": 5, "weekday": 7, "n": 2}, "weekday"),
    ({"kind": "nth_weekday", "month": 5, "weekday": 6, "n": 0}, "n"),
    ({"kind": "nth_weekday", "month": 5, "weekday": 6, "n": 2, "days": 0}, "days"),
    ({"kind": "dates", "dates": [{"from": "2026-12-12", "to": "2026-12-04"}]}, "dates"),
    ({"kind": "dates", "dates": [{"from": "2026-02-30", "to": "2026-03-01"}]}, "dates"),
    ({"kind": "dates", "dates": "kaputt"}, "dates"),
    ({"kind": "dates", "dates": [{"from": "2026-01-01", "to": "2026-03-01"}]}, "dates"),     # > 40 Tage
])
def test_validierung_neue_arten(rule, fehler):
    errs = cal.validate_rule({"id": "x", "name": "n", "enabled": True, "priority": 10, "videos": [], **rule})
    assert errs and any(e.startswith(f"{fehler}:") for e in errs), errs


def test_vorlagen_neue_feiertage():
    by = {t["name"]: t for t in cal.TEMPLATES}
    for name in ("1. Advent", "2. Advent", "3. Advent", "4. Advent", "Muttertag", "Chanukka", "Ramadan", "Zuckerfest",
                 "Nikolaus", "Valentinstag", "Karneval", "St. Martin"):
        assert name in by, name
        assert cal.validate_rule({**by[name], "id": "x", "videos": [], "enabled": True}) == []
    # Stichproben gegen berechnete Termine (convertdate/hijridate, siehe SPEC)
    assert cal.matches(by["Chanukka"], dt.datetime(2026, 12, 5)) and cal.matches(by["Chanukka"], dt.datetime(2030, 12, 25))
    assert cal.matches(by["Ramadan"], dt.datetime(2027, 2, 20)) and not cal.matches(by["Ramadan"], dt.datetime(2027, 3, 9))
    assert cal.matches(by["Zuckerfest"], dt.datetime(2027, 3, 9))
    assert cal.matches(by["Karneval"], dt.datetime(2027, 2, 8))          # Rosenmontag 2027 = Ostern 28.03. − 48
    assert cal.matches(by["Muttertag"], dt.datetime(2027, 5, 9))


def test_advent_sonntag_gewinnt_vor_adventszeit():
    rules = [R(name="Advent", kind="advent", priority=40, videos=["advent.mp4"]),
             R(name="2. Advent", kind="advent_sunday", n=2, priority=45, videos=["advent2.mp4"])]
    c = cal.choose({"rules": rules}, dt.datetime(2026, 12, 8), {"advent.mp4", "advent2.mp4"})
    assert c.videos == ["advent2.mp4"] and c.holiday == "2. Advent"
