"""Fristenrechner ohne KI: §§ 187, 188, 193 BGB + Feiertage je Bundesland (Plan L2 Schritt 1).

Jede Erwartung ist von Hand nachgerechnet (Wochentage mit Python ``date.weekday`` geprüft, 20.10.2026).
Feiertage: DGB-Übersicht 2026–2028; bewegliche Feiertage über die Osterformel (stimmt für 2026–2028 mit DGB überein).
"""
from __future__ import annotations

from datetime import date

import pytest
from backend import deadlines as dl
from backend import holidays_de as hol


def D(s: str) -> date:
    return date.fromisoformat(s)


# ── Feiertage ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("year,easter", [(2026, "2026-04-05"), (2027, "2027-03-28"), (2028, "2028-04-16")])
def test_easter_matches_dgb(year, easter):
    assert hol.easter_sunday(year) == D(easter)


def test_nationwide_holidays_2026():
    h = hol.holidays(2026, "NW")
    for day in ("2026-01-01", "2026-04-03", "2026-04-06", "2026-05-01", "2026-05-14", "2026-05-25",
                "2026-10-03", "2026-12-25", "2026-12-26"):
        assert D(day) in h, day


@pytest.mark.parametrize("day,state,yes", [
    ("2026-06-04", "NW", True), ("2026-06-04", "NI", False),          # Fronleichnam
    ("2026-10-31", "NI", True), ("2026-10-31", "NW", False),          # Reformationstag
    ("2026-11-01", "NW", True), ("2026-11-01", "NI", False),          # Allerheiligen
    ("2026-11-18", "SN", True), ("2026-11-18", "BY", False),          # Buß- und Bettag nur Sachsen
    ("2027-03-08", "BE", True), ("2027-03-08", "MV", True), ("2027-03-08", "HH", False),   # Frauentag
    ("2027-09-20", "TH", True), ("2027-09-20", "SN", False),          # Weltkindertag
    ("2027-01-06", "BW", True), ("2027-01-06", "ST", True), ("2027-01-06", "NW", False),   # Hl. Drei Könige
    ("2028-08-15", "SL", True),                                        # Mariä Himmelfahrt (Saarland ganz)
])
def test_state_holidays(day, state, yes):
    assert (D(day) in hol.holidays(D(day).year, state)) is yes


@pytest.mark.parametrize("state,name", [("BY", "Mariä Himmelfahrt"), ("BY", "Augsburger Friedensfest"),
                                        ("SN", "Fronleichnam"), ("TH", "Fronleichnam")])
def test_partial_holidays_are_not_counted_but_reported(state, name):
    """Nur in einzelnen Gemeinden Feiertag (DGB): nicht einrechnen, aber benennen."""
    year = 2028
    partial = hol.partial_holidays(year, state)
    assert name in {p.name for p in partial}
    assert all(p.day not in hol.holidays(year, state) for p in partial if p.name == name)


def test_unknown_state_is_an_error():
    with pytest.raises(ValueError):
        hol.holidays(2026, "XX")


# ── Fristen ───────────────────────────────────────────────────────────────────

def calc(event, kind, amount, state="NW", start="event"):
    return dl.compute(event_date=D(event), kind=kind, amount=amount, state=state, start=start)


@pytest.mark.parametrize("event,kind,n,due,why", [
    ("2026-10-22", "days", 14, "2026-11-05", "§187 I + §188 I: 22.10. zählt nicht; Do → Do, Allerheiligen So innerhalb"),
    ("2026-10-21", "weeks", 2, "2026-11-04", "§188 II: Mi → Mi zwei Wochen später"),
    ("2026-01-31", "months", 1, "2026-03-02", "§188 III → Sa 28.02.; §193 → Mo 02.03."),
    ("2028-01-31", "months", 1, "2028-02-29", "§188 III Schaltjahr → Di 29.02."),
    ("2026-04-30", "months", 1, "2026-06-01", "§188 II → Sa 30.05.; §193 → Mo 01.06."),
    ("2026-11-28", "months", 1, "2026-12-28", "Sa → Mo 28.12., Werktag"),
    ("2026-11-25", "months", 1, "2026-12-28", "Fr 25.12. Feiertag, Sa, So 27.12. → Mo 28.12."),
    ("2028-02-29", "years", 1, "2029-02-28", "§188 III: kein 29.02.2029 → Mi 28.02."),
    ("2026-12-30", "days", 3, "2027-01-04", "Sa 02.01. → Mo 04.01."),
    ("2026-10-30", "days", 7, "2026-11-06", "Fr → Fr, Werktag"),
    ("2026-04-02", "days", 1, "2026-04-07", "Fr 03.04. Karfreitag, Sa, So Ostern, Mo Ostermontag → Di 07.04."),
])
def test_deadline_cases_nrw(event, kind, n, due, why):
    assert calc(event, kind, n)["due_date"] == due, why


@pytest.mark.parametrize("event,kind,n,state,due,why", [
    ("2026-10-21", "days", 10, "NI", "2026-11-02", "Sa 31.10. (Reformationstag), So → Mo 02.11."),
    ("2026-10-21", "days", 10, "NW", "2026-11-02", "Sa 31.10. → Mo 02.11. (Allerheiligen So, kein Einfluss)"),
    ("2026-06-01", "days", 3, "NW", "2026-06-05", "Do 04.06. Fronleichnam NRW → Fr 05.06."),
    ("2026-06-01", "days", 3, "NI", "2026-06-04", "Do 04.06. in Niedersachsen Werktag"),
    ("2026-11-16", "days", 2, "SN", "2026-11-19", "Mi 18.11. Buß- und Bettag Sachsen → Do 19.11."),
    ("2026-11-16", "days", 2, "BY", "2026-11-18", "in Bayern Werktag"),
    ("2027-02-08", "months", 1, "BE", "2027-03-09", "Mo 08.03.2027 Frauentag Berlin → Di 09.03."),
    ("2027-08-20", "months", 1, "TH", "2027-09-21", "Mo 20.09.2027 Weltkindertag Thüringen → Di 21.09."),
])
def test_deadline_depends_on_state(event, kind, n, state, due, why):
    assert calc(event, kind, n, state=state)["due_date"] == due, why


def test_day_start_rule_187_2():
    """§ 187 Abs. 2: Beginn eines Tages maßgebend → Tag zählt mit; § 188 II: Ende am Vortag des entsprechenden Tages.
    Mietbeginn So 01.03.2026, 1 Monat → Di 31.03.2026."""
    assert calc("2026-03-01", "months", 1, start="day_start")["due_date"] == "2026-03-31"
    assert calc("2026-03-01", "days", 10, start="day_start")["due_date"] == "2026-03-10"


def test_fixed_date_only_applies_193():
    """Bestimmter Tag (kein Zeitraum): nur § 193 – Sa 31.10.2026 → Mo 02.11.2026."""
    assert calc("2026-10-31", "date", 0, state="NW")["due_date"] == "2026-11-02"


def test_result_explains_the_calculation():
    r = calc("2026-01-31", "months", 1)
    assert r["raw_end"] == "2026-02-28"
    assert r["due_date"] == "2026-03-02"
    text = " ".join(r["steps"])
    assert "§ 187 Abs. 1" in text and "§ 188 Abs. 3" in text and "§ 193" in text
    assert "Sonnabend" in text or "Samstag" in text
    assert r["weekday"] == "Montag"


def test_partial_holiday_on_due_date_is_flagged():
    """Fällt das Ende in Bayern auf Mariä Himmelfahrt (Di 15.08.2028), bleibt es dabei – mit Hinweis."""
    r = calc("2028-08-01", "weeks", 2, state="BY")
    assert r["due_date"] == "2028-08-15"
    assert any("Mariä Himmelfahrt" in w and "Gemeinde" in w for w in r["warnings"])


def test_always_says_it_is_no_legal_advice():
    r = calc("2026-10-22", "days", 14)
    assert any("Kein Rechtsrat" in w or "ohne Gewähr" in w for w in r["warnings"])


@pytest.mark.parametrize("kwargs", [
    {"kind": "hours", "amount": 3}, {"kind": "days", "amount": -1}, {"kind": "days", "amount": 100_000},
    {"kind": "days", "amount": 3, "state": "XX"}, {"kind": "days", "amount": 3, "start": "irgendwann"},
])
def test_invalid_input(kwargs):
    args = {"event_date": D("2026-10-22"), "kind": "days", "amount": 3, "state": "NW", "start": "event", **kwargs}
    with pytest.raises(ValueError):
        dl.compute(**args)
