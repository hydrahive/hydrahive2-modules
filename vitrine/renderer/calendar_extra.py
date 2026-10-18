"""Zusätzliche Feiertagsarten für den Kalender (aus calendar.py ausgelagert, damit die Datei klein bleibt).

  advent_sunday  n-ter Adventssonntag (1–4): vom Sonntag bis Samstag davor, der 4. nur bis 23.12.
  nth_weekday    n-ter Wochentag im Monat (n 1–5, −1 = letzter; weekday 0 = Mo … 6 = So), `days` Tage lang
  dates          Termine je Jahr: Liste von {from, to} als JJJJ-MM-TT (für Chanukka, Ramadan – nicht einfach berechenbar)
"""
from __future__ import annotations

import datetime as dt
import re

KINDS = ("advent_sunday", "nth_weekday", "dates")
MAX_DATES = 40            # Einträge je Regel
MAX_SPAN_DAYS = 40        # ein Zeitraum (Ramadan ≈ 30 Tage)
_YMD = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def first_advent(year: int) -> dt.date:
    christmas_eve = dt.date(year, 12, 24)
    fourth = christmas_eve - dt.timedelta(days=(christmas_eve.weekday() + 1) % 7)
    return fourth - dt.timedelta(weeks=3)


def _int(v) -> int | None:
    if isinstance(v, bool):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _ymd(s) -> dt.date | None:
    if not _YMD.match(str(s or "")):
        return None
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        return None


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date | None:
    """n-ter Wochentag im Monat; n = −1 ist der letzte. None, wenn es ihn nicht gibt (z. B. 5. Sonntag im Februar)."""
    if n == -1:
        last = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1))
        return last - dt.timedelta(days=(last.weekday() - weekday) % 7)
    first = dt.date(year, month, 1)
    d = first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))
    return d if d.month == month else None


def _periods(rule: dict) -> list[tuple[dt.date, dt.date]]:
    out = []
    for p in rule.get("dates") if isinstance(rule.get("dates"), list) else []:
        a, b = (_ymd(p.get("from")), _ymd(p.get("to"))) if isinstance(p, dict) else (None, None)
        if a and b and a <= b:
            out.append((a, b))
    return out


def matches(rule: dict, day: dt.date) -> bool:
    kind = rule.get("kind")
    if kind == "advent_sunday":
        n = _int(rule.get("n"))
        if n not in (1, 2, 3, 4):
            return False
        start = first_advent(day.year) + dt.timedelta(weeks=n - 1)
        end = min(start + dt.timedelta(days=6), dt.date(day.year, 12, 23))
        return start <= day <= end
    if kind == "nth_weekday":
        month, weekday, n, days = (_int(rule.get(k)) for k in ("month", "weekday", "n", "days"))
        days = 1 if rule.get("days") is None else days
        if not (month and 1 <= month <= 12 and weekday is not None and 0 <= weekday <= 6 and n in (-1, 1, 2, 3, 4, 5)
                and days and days >= 1):
            return False
        start = nth_weekday(day.year, month, weekday, n)
        return start is not None and start <= day < start + dt.timedelta(days=days)
    if kind == "dates":
        return any(a <= day <= b for a, b in _periods(rule))
    return False


def validate(rule: dict) -> list[str]:
    kind, errs = rule.get("kind"), []
    if kind == "advent_sunday":
        if _int(rule.get("n")) not in (1, 2, 3, 4):
            errs.append("n: 1, 2, 3 oder 4 erwartet")
    elif kind == "nth_weekday":
        month, weekday, n = _int(rule.get("month")), _int(rule.get("weekday")), _int(rule.get("n"))
        if month is None or not 1 <= month <= 12:
            errs.append("month: 1–12 erwartet")
        if weekday is None or not 0 <= weekday <= 6:
            errs.append("weekday: 0 (Mo) bis 6 (So) erwartet")
        if n not in (-1, 1, 2, 3, 4, 5):
            errs.append("n: 1–5 oder -1 (letzter) erwartet")
        if rule.get("days") is not None and not 1 <= (_int(rule.get("days")) or 0) <= 31:
            errs.append("days: 1–31 erwartet")
    elif kind == "dates":
        items = rule.get("dates")
        if not isinstance(items, list) or len(items) > MAX_DATES:
            return [f"dates: Liste mit höchstens {MAX_DATES} Zeiträumen erwartet"]
        for i, p in enumerate(items):
            a, b = (_ymd(p.get("from")), _ymd(p.get("to"))) if isinstance(p, dict) else (None, None)
            if not (a and b):
                errs.append(f"dates: Zeitraum {i + 1} braucht from/to als JJJJ-MM-TT")
            elif a > b or (b - a).days > MAX_SPAN_DAYS:
                errs.append(f"dates: Zeitraum {i + 1} muss vorwärts laufen und ≤ {MAX_SPAN_DAYS} Tage lang sein")
    return errs


def clean(rule: dict) -> dict:
    """Nur die Felder der neuen Arten, die gespeichert werden (Backend nutzt das beim PUT /config)."""
    kind = rule.get("kind")
    if kind == "advent_sunday":
        return {"n": int(rule["n"])}
    if kind == "nth_weekday":
        out = {k: int(rule[k]) for k in ("month", "weekday", "n")}
        return {**out, "days": int(rule["days"])} if rule.get("days") is not None else out
    if kind == "dates":
        return {"dates": [{"from": str(p["from"]), "to": str(p["to"])} for p in rule["dates"]]}
    return {}
