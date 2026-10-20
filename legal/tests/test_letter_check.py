"""Prüfliste für Briefe ohne KI (Plan L3 Schritt 2, Spec §4.7). Nichts blockiert – die Liste zeigt, was fehlt.

check(letter, case=…, today=…) → {"items": [{key, ok, hint}], "norms": [{raw, citation, found}], "ok": bool}
"""
from __future__ import annotations

from datetime import date

import pytest
from backend import corpus_store, letter_check
from backend.gii_parse import parse_law
from conftest import fixture_xml

TODAY = date(2026, 10, 20)
GOOD = {
    "sender": "Till Muster\nMusterweg 1\n30159 Hannover",
    "recipient": "Hausverwaltung Müller GmbH\nHauptstraße 1\n30159 Hannover",
    "date": "2026-10-20",
    "subject": "Mangelanzeige Wohnung Musterweg 1, 2. OG – Überhitzung",
    "body": ("Sehr geehrte Damen und Herren,\n\nhiermit zeige ich gemäß § 536c BGB an, dass die Wohnung seit Juni 2026 dauerhaft "
             "über 28 °C warm ist. Ich fordere Sie auf, den Mangel bis zum 10.11.2026 zu beseitigen.\n\n"
             "Anlage: Messprotokoll 28.06.–16.08.2026\n\nMit freundlichen Grüßen"),
    "delivery": "einwurf_einschreiben",
    "attachments": ["Messprotokoll 28.06.–16.08.2026"],
    "their_ref": "",
}


@pytest.fixture(autouse=True)
def corpus():
    xml = fixture_xml("bgb")
    corpus_store.save_law(parse_law("bgb", xml), xml, fetched_at="2026-10-20T03:30:00Z", pinned=True)


def _items(letter, **kw):
    out = letter_check.check(letter, today=TODAY, **kw)
    return {i["key"]: i for i in out["items"]}, out


def test_good_letter_all_ok():
    items, out = _items(GOOD)
    assert all(i["ok"] for i in items.values()), [i for i in items.values() if not i["ok"]]
    assert out["ok"] is True
    assert out["norms"] == [{"raw": "§ 536c BGB", "citation": "§ 536c BGB", "found": True}]
    assert set(items) == {"sender", "recipient", "date", "subject", "reference", "deadline_date", "deadline_future",
                          "norms", "delivery", "attachments"}


@pytest.mark.parametrize("field,value,key", [
    ("sender", "", "sender"),
    ("sender", "Till Muster", "sender"),                     # Name ohne Anschrift
    ("recipient", "Hausverwaltung", "recipient"),
    ("date", "", "date"),
    ("date", "20.10.2026", "date"),                          # erwartet ISO aus dem Editor
    ("subject", "  ", "subject"),
    ("delivery", "", "delivery"),
])
def test_missing_basics(field, value, key):
    items, out = _items({**GOOD, field: value})
    assert items[key]["ok"] is False and items[key]["hint"]
    assert out["ok"] is False


@pytest.mark.parametrize("phrase", [
    "binnen 14 Tagen", "innerhalb von zwei Wochen", "innerhalb einer Woche", "in 3 Wochen", "binnen eines Monats",
    "innerhalb von 10 Werktagen",
])
def test_relative_deadline_without_date_is_flagged(phrase):
    body = f"Ich fordere Sie auf, den Mangel {phrase} zu beseitigen. § 536c BGB."
    items, _ = _items({**GOOD, "body": body})
    assert items["deadline_date"]["ok"] is False
    assert "Datum" in items["deadline_date"]["hint"]


def test_relative_deadline_with_date_in_same_sentence_is_ok():
    body = "Ich fordere Sie auf, den Mangel binnen 14 Tagen, also bis zum 03.11.2026, zu beseitigen. § 536c BGB."
    items, _ = _items({**GOOD, "body": body})
    assert items["deadline_date"]["ok"] is True


def test_deadline_in_the_past_is_flagged():
    body = "Bitte beseitigen Sie den Mangel bis zum 01.10.2026. § 536c BGB."
    items, _ = _items({**GOOD, "body": body})
    assert items["deadline_future"]["ok"] is False and "01.10.2026" in items["deadline_future"]["hint"]


def test_deadline_before_letter_date_counts_not_today():
    body = "Bitte beseitigen Sie den Mangel bis zum 25.10.2026. § 536c BGB."
    items, _ = _items({**GOOD, "body": body, "date": "2026-10-30"})
    assert items["deadline_future"]["ok"] is False


def test_unknown_or_missing_norms_are_red_but_do_not_hide_others():
    body = "Gemäß § 536c BGB und § 999 BGB sowie § 5 WiStG fordere ich Abhilfe bis zum 10.11.2026."
    items, out = _items({**GOOD, "body": body})
    assert out["norms"] == [
        {"raw": "§ 536c BGB", "citation": "§ 536c BGB", "found": True},
        {"raw": "§ 999 BGB", "citation": "§ 999 BGB", "found": False},
        {"raw": "§ 5 WiStG", "citation": "§ 5 WiStG", "found": False},
    ]
    assert items["norms"]["ok"] is False and "§ 999 BGB" in items["norms"]["hint"] and "§ 5 WiStG" in items["norms"]["hint"]


def test_no_norms_at_all_is_a_hint():
    items, _ = _items({**GOOD, "body": "Bitte beseitigen Sie den Mangel bis zum 10.11.2026."})
    assert items["norms"]["ok"] is False and "keine Norm" in items["norms"]["hint"]


def test_attachment_mentioned_but_not_listed():
    items, _ = _items({**GOOD, "attachments": []})
    assert items["attachments"]["ok"] is False
    items, _ = _items({**GOOD, "attachments": [], "body": GOOD["body"].replace("Anlage: Messprotokoll 28.06.–16.08.2026\n\n", "")})
    assert items["attachments"]["ok"] is True


def test_reference_required_only_if_case_has_one():
    items, _ = _items(GOOD, case={"their_ref": "Az. 12/345"})
    assert items["reference"]["ok"] is False and "12/345" in items["reference"]["hint"]
    items, _ = _items({**GOOD, "their_ref": "Az. 12/345"}, case={"their_ref": "Az. 12/345"})
    assert items["reference"]["ok"] is True
    items, _ = _items({**GOOD, "subject": GOOD["subject"] + " (Ihr Zeichen 12/345)"}, case={"their_ref": "12/345"})
    assert items["reference"]["ok"] is True


def test_garbage_input_does_not_crash():
    out = letter_check.check({}, today=TODAY)
    assert out["ok"] is False and len(out["items"]) == 10
    out = letter_check.check({"body": None, "attachments": "kaputt", "date": "2026-13-45"}, today=TODAY)
    assert out["ok"] is False


@pytest.mark.parametrize("body", [
    "Am 03.07.2026 habe ich den Mangel mündlich gemeldet.\nBitte beseitigen Sie ihn binnen 14 Tagen. § 536c BGB.",
    "Am 03.07.2026 habe ich den Mangel mündlich gemeldet. Bitte beseitigen Sie ihn binnen 14 Tagen. § 536c BGB.",
    "Bitte beseitigen Sie den Mangel binnen 14 Tagen. Die Messung vom 16.08.2026 liegt bei. § 536c BGB.",
])
def test_date_in_neighbouring_sentence_does_not_count(body):
    """Nur ein Datum im SELBEN Satz macht die relative Frist bestimmt – ein Datum davor/danach (Ereignis) nicht."""
    items, _ = _items({**GOOD, "body": body})
    assert items["deadline_date"]["ok"] is False
