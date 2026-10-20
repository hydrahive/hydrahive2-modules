"""Aktenzeichen-Prüfung darf nicht über Teilstücke („1“, „2026“) falsch grün werden (Gegenprobe Plan L3 Schritt 2)."""
from __future__ import annotations

from datetime import date

import pytest
from backend import letter_check
from test_letter_check import GOOD


@pytest.mark.parametrize("ref,subject,their_ref,ok", [
    ("Az. 1", "Mangelanzeige Wohnung 1. OG", "", False),
    ("Az 2026", "Schreiben vom 20.10.2026", "", False),
    ("XY-77/2026", "Mangelanzeige", "", False),
    ("Az. 12/345", "Ihr Zeichen 12/345", "", True),
    ("Az. 12/345", "Mangelanzeige", "Az. 12/345", True),
    ("12/345", "Mangelanzeige", "12/345", True),
    ("Az. 12/345", "Mangelanzeige", "12 / 345", True),
])
def test_reference_matching(ref, subject, their_ref, ok):
    items = {i["key"]: i for i in letter_check.check({**GOOD, "subject": subject, "their_ref": their_ref},
                                                      case={"their_ref": ref}, today=date(2026, 10, 20))["items"]}
    assert items["reference"]["ok"] is ok


@pytest.mark.parametrize("subject", ["Ihr Zeichen 12/345.", "Mangel (Az. 12/345)", "Az. 12/345 – Mangelanzeige"])
def test_reference_at_sentence_end_or_in_brackets(subject):
    items = {i["key"]: i for i in letter_check.check({**GOOD, "subject": subject}, case={"their_ref": "Az. 12/345"},
                                                      today=date(2026, 10, 20))["items"]}
    assert items["reference"]["ok"] is True
