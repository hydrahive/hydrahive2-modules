"""Vorlagen für Kalender-Regeln (im Cockpit wählbar). S8: mit Vorschlag für die Lichtfarbe (Jahreszeiten nicht – die
kommen aus den Licht-Einstellungen).

Chanukka/Ramadan/Zuckerfest: Termine berechnet am 18.10.2026 mit `convertdate` (hebräischer Kalender,
25. Kislew; ab dem Vorabend, an dem das erste Licht brennt) und `hijridate` (Umm-al-Qura-Kalender; Ramadan 1.–letzter
Tag, Zuckerfest 1.–3. Schawwal). Der Ramadan richtet sich je nach Gemeinde nach der Mondsichtung und kann um einen Tag
abweichen. Nach 2035 neue Termine eintragen.

Chanukka hat dieselbe Priorität wie die Adventssonntage: fallen beide zusammen, wechseln sich die Videos ab.
"""
from __future__ import annotations

_CHANUKKA = [("2026-12-04", "2026-12-12"), ("2027-12-24", "2028-01-01"), ("2028-12-12", "2028-12-20"),
             ("2029-12-01", "2029-12-09"), ("2030-12-20", "2030-12-28"), ("2031-12-09", "2031-12-17"),
             ("2032-11-27", "2032-12-05"), ("2033-12-16", "2033-12-24"), ("2034-12-06", "2034-12-14"),
             ("2035-12-25", "2036-01-02")]
_RAMADAN = [("2026-02-18", "2026-03-19"), ("2027-02-08", "2027-03-08"), ("2028-01-28", "2028-02-25"),
            ("2029-01-16", "2029-02-13"), ("2030-01-05", "2030-02-03"), ("2030-12-26", "2031-01-23"),
            ("2031-12-15", "2032-01-13"), ("2032-12-04", "2033-01-01"), ("2033-11-23", "2033-12-22"),
            ("2034-11-12", "2034-12-11"), ("2035-11-01", "2035-11-30")]
_ZUCKERFEST = [("2026-03-20", "2026-03-22"), ("2027-03-09", "2027-03-11"), ("2028-02-26", "2028-02-28"),
               ("2029-02-14", "2029-02-16"), ("2030-02-04", "2030-02-06"), ("2031-01-24", "2031-01-26"),
               ("2032-01-14", "2032-01-16"), ("2033-01-02", "2033-01-04"), ("2033-12-23", "2033-12-25"),
               ("2034-12-12", "2034-12-14"), ("2035-12-01", "2035-12-03")]


def _dates(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"from": a, "to": b} for a, b in pairs]


TEMPLATES = [
    {"name": "Neujahr", "kind": "range", "from": "01-01", "to": "01-01", "priority": 50},
    {"name": "Valentinstag", "kind": "range", "from": "02-14", "to": "02-14", "priority": 50},
    {"name": "Karneval", "kind": "easter", "offset_from": -52, "offset_to": -47, "priority": 50},
    {"name": "Ostern", "kind": "easter", "offset_from": -2, "offset_to": 1, "priority": 50},
    {"name": "Muttertag", "kind": "nth_weekday", "month": 5, "weekday": 6, "n": 2, "priority": 50},
    {"name": "Pfingsten", "kind": "easter", "offset_from": 49, "offset_to": 50, "priority": 50},
    {"name": "Halloween", "kind": "range", "from": "10-31", "to": "10-31", "priority": 50},
    {"name": "St. Martin", "kind": "range", "from": "11-11", "to": "11-11", "priority": 50},
    {"name": "Advent", "kind": "advent", "priority": 40},
    {"name": "1. Advent", "kind": "advent_sunday", "n": 1, "priority": 45},
    {"name": "2. Advent", "kind": "advent_sunday", "n": 2, "priority": 45},
    {"name": "3. Advent", "kind": "advent_sunday", "n": 3, "priority": 45},
    {"name": "4. Advent", "kind": "advent_sunday", "n": 4, "priority": 45},
    {"name": "Nikolaus", "kind": "range", "from": "12-06", "to": "12-06", "priority": 50},
    {"name": "Weihnachten", "kind": "range", "from": "12-24", "to": "12-26", "priority": 60},
    {"name": "Silvester", "kind": "range", "from": "12-31", "to": "12-31", "priority": 60},
    {"name": "Chanukka", "kind": "dates", "dates": _dates(_CHANUKKA), "priority": 45},
    {"name": "Ramadan", "kind": "dates", "dates": _dates(_RAMADAN), "priority": 30},
    {"name": "Zuckerfest", "kind": "dates", "dates": _dates(_ZUCKERFEST), "priority": 50},
    {"name": "Frühling", "kind": "season", "season": "spring", "priority": 10},
    {"name": "Sommer", "kind": "season", "season": "summer", "priority": 10},
    {"name": "Herbst", "kind": "season", "season": "autumn", "priority": 10},
    {"name": "Winter", "kind": "season", "season": "winter", "priority": 10},
]

# S8: Lichtfarbe + Effekt je Vorlage (Vorschlag; im Regel-Editor änderbar oder abschaltbar)
_LIGHT = {
    "Neujahr": ("FFFFFF", "static"), "Valentinstag": ("FF4F9A", "breathing"), "Karneval": ("FF00C8", "flashing"),
    "Ostern": ("FFF06A", "static"), "Muttertag": ("FF7FBF", "static"), "Pfingsten": ("FFE066", "static"),
    "Halloween": ("FF6A00", "breathing"), "St. Martin": ("FFA040", "breathing"), "Advent": ("FFB347", "static"),
    "1. Advent": ("FFB347", "static"), "2. Advent": ("FFB347", "static"), "3. Advent": ("FFB347", "static"),
    "4. Advent": ("FFB347", "static"), "Nikolaus": ("FF2020", "static"), "Weihnachten": ("FF1A1A", "breathing"),
    "Silvester": ("FFFFFF", "flashing"), "Chanukka": ("4F8BFF", "static"), "Ramadan": ("3DDC84", "static"),
    "Zuckerfest": ("3DDC84", "breathing"),
}
for _t in TEMPLATES:
    if _t["name"] in _LIGHT:
        _t["light_color"], _t["light_effect"] = _LIGHT[_t["name"]]
