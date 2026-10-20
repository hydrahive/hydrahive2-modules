"""Fristen nach §§ 187, 188, 193 BGB – ohne KI, mit Rechenweg (Plan L2 Schritt 1).

Wortlaut (gesetze-im-internet.de, 20.10.2026):
- § 187 Abs. 1: Ereignis/Zeitpunkt im Lauf eines Tages → dieser Tag zählt nicht mit.
- § 187 Abs. 2: Beginn eines Tages maßgebend → dieser Tag zählt mit.
- § 188 Abs. 1: Tagesfrist endet mit Ablauf des letzten Tages.
- § 188 Abs. 2: Wochen-/Monats-/Jahresfrist endet bei Abs. 1 am Tag gleicher Benennung/Zahl, bei Abs. 2 am Vortag.
- § 188 Abs. 3: fehlt der Tag im letzten Monat → Ablauf des letzten Tages dieses Monats.
- § 193: Ende auf Sonnabend, Sonntag oder am Erklärungsort staatlich anerkannten allgemeinen Feiertag → nächster Werktag.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from . import holidays_de as hol

KINDS = ("days", "weeks", "months", "years", "date")
STARTS = ("event", "day_start")
MAX_AMOUNT = {"days": 3660, "weeks": 520, "months": 120, "years": 30, "date": 0}
_WD = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
_UNIT = {"days": ("Tag", "Tage"), "weeks": ("Woche", "Wochen"), "months": ("Monat", "Monate"), "years": ("Jahr", "Jahre")}
DISCLAIMER = ("Kein Rechtsrat, ohne Gewähr: Fristbeginn (Zugang!), Sonderregeln (z. B. ZPO, Zustellung) und "
              "Feiertage am Erklärungsort selbst prüfen; im Zweifel früher handeln.")


def _fmt(d: date) -> str:
    return f"{_WD[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def _add_months(d: date, months: int) -> tuple[date, bool]:
    """(Tag gleicher Zahl im Zielmonat, ob § 188 Abs. 3 griff)."""
    y, m = d.year + (d.month - 1 + months) // 12, (d.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last)), d.day > last


def _validate(kind: str, amount: int, state: str, start: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"Unbekannte Fristart {kind!r} (erlaubt: {', '.join(KINDS)})")
    if start not in STARTS:
        raise ValueError(f"Unbekannter Fristbeginn {start!r} (event oder day_start)")
    if not isinstance(amount, int) or amount < 0 or amount > MAX_AMOUNT[kind] or (kind != "date" and amount == 0):
        raise ValueError(f"Ungültige Anzahl {amount!r} für {kind}")
    if state not in hol.STATES:
        raise ValueError(f"Unbekanntes Bundesland: {state!r}")


def compute(*, event_date: date, kind: str, amount: int, state: str, start: str = "event") -> dict:
    _validate(kind, amount, state, start)
    steps: list[str] = []
    warnings: list[str] = []
    if kind == "date":
        raw = event_date
        steps.append(f"Bestimmter Tag: {_fmt(raw)}.")
    else:
        sing, plur = _UNIT[kind]
        unit = sing if amount == 1 else plur
        if start == "event":
            steps.append(f"§ 187 Abs. 1 BGB: Der Ereignistag {_fmt(event_date)} zählt nicht mit.")
        else:
            steps.append(f"§ 187 Abs. 2 BGB: Der Anfangstag {_fmt(event_date)} zählt mit.")
        if kind == "days":
            raw = event_date + timedelta(days=amount - (1 if start == "day_start" else 0))
            steps.append(f"§ 188 Abs. 1 BGB: {amount} {unit} → Ablauf des {_fmt(raw)}.")
        else:
            if kind == "weeks":
                same, short = event_date + timedelta(weeks=amount), False
            else:
                same, short = _add_months(event_date, amount * (12 if kind == "years" else 1))
            raw = same - timedelta(days=1) if start == "day_start" else same
            rule = "Tag gleicher Benennung/Zahl" if start == "event" else "Vortag des Tages gleicher Zahl"
            steps.append(f"§ 188 Abs. 2 BGB: {amount} {unit} → {rule}: {_fmt(raw)}.")
            if short:
                steps.append(f"§ 188 Abs. 3 BGB: Diesen Tag gibt es im Zielmonat nicht → letzter Tag des Monats, {_fmt(raw)}.")
    due = raw
    skipped: list[str] = []
    while due.weekday() >= 5 or due in hol.holidays(due.year, state):
        name = hol.holiday_name(due, state)
        skipped.append(f"{_fmt(due)} ({name or ('Sonnabend' if due.weekday() == 5 else 'Sonntag')})")
        due += timedelta(days=1)
    if skipped:
        steps.append(f"§ 193 BGB: {'; '.join(skipped)} ist kein Werktag → nächster Werktag {_fmt(due)}.")
    else:
        steps.append(f"§ 193 BGB: {_fmt(due)} ist ein Werktag in {hol.STATES[state]} – keine Verschiebung.")
    for p in hol.partial_holidays(due.year, state):
        if p.day == due:
            warnings.append(f"{_fmt(due)} ist {p.name} – in {hol.STATES[state]} nur in einzelnen Gemeinden Feiertag. "
                            "Gilt er am Erklärungsort, endet die Frist erst am nächsten Werktag.")
    warnings.append(DISCLAIMER)
    return {
        "event_date": event_date.isoformat(), "kind": kind, "amount": amount, "state": state, "start": start,
        "raw_end": raw.isoformat(), "due_date": due.isoformat(), "weekday": _WD[due.weekday()],
        "steps": steps, "warnings": warnings,
    }
