"""Gesetzliche Feiertage je Bundesland (für § 193 BGB). Ohne Abhängigkeit.

Quelle: DGB-Übersicht „Gesetzliche Feiertage 2026–2028“ (dgb.de/service/ratgeber/feiertage, abgerufen 20.10.2026,
„ohne Gewähr“); maßgeblich sind die Feiertagsgesetze der Länder. Bewegliche Feiertage über die Osterformel – für 2026,
2027 und 2028 mit allen DGB-Daten (Karfreitag … Fronleichnam, Buß- und Bettag) abgeglichen.

Nur in einzelnen Gemeinden geltende Feiertage (Fronleichnam in Teilen Sachsens/Thüringens, Mariä Himmelfahrt in
überwiegend katholischen Gemeinden Bayerns, Augsburger Friedensfest) werden NICHT eingerechnet, sondern gemeldet.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

STATES: dict[str, str] = {
    "BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin", "BB": "Brandenburg", "HB": "Bremen",
    "HH": "Hamburg", "HE": "Hessen", "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SL": "Saarland", "SN": "Sachsen",
    "ST": "Sachsen-Anhalt", "SH": "Schleswig-Holstein", "TH": "Thüringen",
}


@dataclass(frozen=True)
class Holiday:
    day: date
    name: str


def easter_sunday(year: int) -> date:
    """Gregorianischer Ostersonntag (Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _repentance_day(year: int) -> date:
    """Buß- und Bettag: Mittwoch vor dem 23. November."""
    d = date(year, 11, 22)
    while d.weekday() != 2:
        d -= timedelta(days=1)
    return d


def _all_named(year: int) -> dict[str, date]:
    e = easter_sunday(year)
    return {
        "Neujahr": date(year, 1, 1), "Heilige Drei Könige": date(year, 1, 6),
        "Internationaler Frauentag": date(year, 3, 8), "Karfreitag": e - timedelta(days=2),
        "Ostersonntag": e, "Ostermontag": e + timedelta(days=1), "Tag der Arbeit": date(year, 5, 1),
        "Christi Himmelfahrt": e + timedelta(days=39), "Pfingstsonntag": e + timedelta(days=49),
        "Pfingstmontag": e + timedelta(days=50), "Fronleichnam": e + timedelta(days=60),
        "Augsburger Friedensfest": date(year, 8, 8), "Mariä Himmelfahrt": date(year, 8, 15),
        "Weltkindertag": date(year, 9, 20), "Tag der Deutschen Einheit": date(year, 10, 3),
        "Reformationstag": date(year, 10, 31), "Allerheiligen": date(year, 11, 1),
        "Buß- und Bettag": _repentance_day(year), "1. Weihnachtsfeiertag": date(year, 12, 25),
        "2. Weihnachtsfeiertag": date(year, 12, 26),
    }


_NATIONWIDE = ("Neujahr", "Karfreitag", "Ostermontag", "Tag der Arbeit", "Christi Himmelfahrt", "Pfingstmontag",
               "Tag der Deutschen Einheit", "1. Weihnachtsfeiertag", "2. Weihnachtsfeiertag")

_STATE_WIDE: dict[str, tuple[str, ...]] = {
    "BW": ("Heilige Drei Könige", "Fronleichnam", "Allerheiligen"),
    "BY": ("Heilige Drei Könige", "Fronleichnam", "Allerheiligen"),
    "BE": ("Internationaler Frauentag",),
    "BB": ("Ostersonntag", "Pfingstsonntag", "Reformationstag"),
    "HB": ("Reformationstag",),
    "HH": ("Reformationstag",),
    "HE": ("Fronleichnam",),
    "MV": ("Internationaler Frauentag", "Reformationstag"),
    "NI": ("Reformationstag",),
    "NW": ("Fronleichnam", "Allerheiligen"),
    "RP": ("Fronleichnam", "Allerheiligen"),
    "SL": ("Fronleichnam", "Mariä Himmelfahrt", "Allerheiligen"),
    "SN": ("Reformationstag", "Buß- und Bettag"),
    "ST": ("Heilige Drei Könige", "Reformationstag"),
    "SH": ("Reformationstag",),
    "TH": ("Weltkindertag", "Reformationstag"),
}

_PARTIAL: dict[str, tuple[str, ...]] = {
    "BY": ("Augsburger Friedensfest", "Mariä Himmelfahrt"),
    "SN": ("Fronleichnam",),
    "TH": ("Fronleichnam",),
}


def _check(state: str) -> str:
    if state not in STATES:
        raise ValueError(f"Unbekanntes Bundesland: {state!r} (erlaubt: {', '.join(STATES)})")
    return state


def named_holidays(year: int, state: str) -> list[Holiday]:
    named = _all_named(year)
    names = _NATIONWIDE + _STATE_WIDE[_check(state)]
    return sorted((Holiday(named[n], n) for n in names), key=lambda h: h.day)


def holidays(year: int, state: str) -> set[date]:
    return {h.day for h in named_holidays(year, state)}


def partial_holidays(year: int, state: str) -> list[Holiday]:
    named = _all_named(year)
    return [Holiday(named[n], n) for n in _PARTIAL.get(_check(state), ())]


def holiday_name(day: date, state: str) -> str | None:
    return next((h.name for h in named_holidays(day.year, state) if h.day == day), None)
