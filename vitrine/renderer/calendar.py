"""Kalender-Regeln: welches Video läuft wann. Gleiche Logik für den Dienst und die Cockpit-Vorschau.

Regel-Arten:
  range   MM-TT bis MM-TT (auch über Jahreswechsel, Ende einschließlich)
  easter  Tage relativ zum Ostersonntag (offset_from..offset_to, einschließlich)
  advent  1. Advent bis 23.12.
  season  meteorologisch: spring 03-01, summer 06-01, autumn 09-01, winter 12-01
  time    HH:MM bis HH:MM (auch über Mitternacht, Ende ausschließlich)
  advent_sunday, nth_weekday, dates – siehe calendar_extra (einzelne Advente, Muttertag, Chanukka/Ramadan)
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from . import calendar_extra as extra
from .calendar_templates import TEMPLATES

KINDS = ("range", "easter", "advent", "season", "time", *extra.KINDS)
HOLIDAY_KINDS = {"range", "easter", "advent", *extra.KINDS}
SEASONS = {"spring": (3, 5), "summer": (6, 8), "autumn": (9, 11), "winter": (12, 2)}

_MD = re.compile(r"^(\d{2})-(\d{2})$")
_HM = re.compile(r"^(\d{2}):(\d{2})$")


@dataclass
class Choice:
    videos: list[str] = field(default_factory=list)
    rule: str | None = None
    holiday: str | None = None


def easter(year: int) -> dt.date:
    """Ostersonntag (gregorianisch, anonymer Algorithmus nach Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return dt.date(year, month, day + 1)


first_advent = extra.first_advent


def _md(s) -> tuple[int, int] | None:
    m = _MD.match(str(s or ""))
    if not m:
        return None
    mo, d = int(m[1]), int(m[2])
    try:
        dt.date(2024, mo, d)          # Schaltjahr: 02-29 ist erlaubt
    except ValueError:
        return None
    return mo, d


def _hm(s) -> int | None:
    m = _HM.match(str(s or ""))
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return None
    return int(m[1]) * 60 + int(m[2])


def matches(rule: dict, now: dt.datetime) -> bool:
    kind = rule.get("kind")
    today = (now.month, now.day)
    if kind == "range":
        a, b = _md(rule.get("from")), _md(rule.get("to"))
        if not (a and b):
            return False
        return a <= today <= b if a <= b else (today >= a or today <= b)
    if kind == "easter":
        try:
            lo, hi = int(rule.get("offset_from")), int(rule.get("offset_to"))
        except (TypeError, ValueError):
            return False
        delta = (now.date() - easter(now.year)).days
        return lo <= delta <= hi
    if kind == "advent":
        return first_advent(now.year) <= now.date() <= dt.date(now.year, 12, 23)
    if kind == "season":
        rng = SEASONS.get(rule.get("season"))
        if not rng:
            return False
        a, b = rng
        return a <= now.month <= b if a <= b else (now.month >= a or now.month <= b)
    if kind == "time":
        a, b = _hm(rule.get("from")), _hm(rule.get("to"))
        if a is None or b is None:
            return False
        t = now.hour * 60 + now.minute
        return a <= t < b if a <= b else (t >= a or t < b)
    if kind in extra.KINDS:
        return extra.matches(rule, now.date())
    return False


def choose(config: dict, now: dt.datetime, available: set[str]) -> Choice:
    best: list[dict] = []
    for r in config.get("rules") or []:
        if not r.get("enabled", True) or not matches(r, now):
            continue
        if not any(v in available for v in r.get("videos") or []):
            continue
        if not best or r.get("priority", 0) > best[0].get("priority", 0):
            best = [r]
        elif r.get("priority", 0) == best[0].get("priority", 0):
            best.append(r)
    if best:
        vids: list[str] = []
        for r in best:
            vids += [v for v in r.get("videos") or [] if v in available and v not in vids]
        holiday = next((r["name"] for r in best if r.get("kind") in HOLIDAY_KINDS), None)
        return Choice(vids, best[0].get("name"), holiday)
    default = [v for v in config.get("default_videos") or [] if v in available]
    return Choice(default or sorted(available))


def rotate(videos: list[str], now: dt.datetime, minutes: int) -> str | None:
    """Welches der Videos gerade dran ist – aus der Uhrzeit berechnet, damit es nach einem Neustart gleich bleibt."""
    if not videos:
        return None
    if minutes <= 0 or len(videos) == 1:
        return videos[0]
    slot = int(now.timestamp() // (minutes * 60))
    return videos[slot % len(videos)]


def validate_rule(rule: dict) -> list[str]:
    """Fehlertexte (leer = gültig). Wird vom Backend für PUT /config benutzt."""
    errs: list[str] = []
    kind = rule.get("kind")
    if kind not in KINDS:
        return [f"kind: unbekannte Art {kind!r}"]
    if not str(rule.get("name") or "").strip():
        errs.append("name: fehlt")
    if kind == "range":
        for key in ("from", "to"):
            if _md(rule.get(key)) is None:
                errs.append(f"{key}: Datum als MM-TT erwartet")
    elif kind == "time":
        for key in ("from", "to"):
            if _hm(rule.get(key)) is None:
                errs.append(f"{key}: Uhrzeit als HH:MM erwartet")
    elif kind == "season" and rule.get("season") not in SEASONS:
        errs.append("season: spring, summer, autumn oder winter")
    elif kind == "easter":
        try:
            lo, hi = int(rule.get("offset_from")), int(rule.get("offset_to"))
            if not (-120 <= lo <= hi <= 120):
                errs.append("offset: -120 ≤ offset_from ≤ offset_to ≤ 120")
        except (TypeError, ValueError):
            errs.append("offset: ganze Zahlen erwartet")
    elif kind in extra.KINDS:
        errs += extra.validate(rule)
    return errs
