"""Querverweise nach einer Normbezeichnung: nur Nennungen DIESES Gesetzes (gemessen am echten BGB, 20.10.2026)."""
from __future__ import annotations

import pytest
from backend.search import cites_number


@pytest.mark.parametrize("text", [
    "die in § 536 bestimmten Rechte",
    "nach den §§ 535, 536 und 543",
    "gemäß §§ 536 bis 536d",
    "§ 536 Abs. 1 gilt entsprechend",
    "nach § 536 Absatz 1 Satz 2 dieses Gesetzes",
])
def test_counts_own_law_mentions(text):
    assert cites_number(text, "536")


@pytest.mark.parametrize("text", [
    "nach § 536a Abs. 1 Schadensersatz",                       # andere Norm
    "siehe § 5361",                                            # andere Nummer
    "§ 1 Absatz 1 Satz 2 des Kreditwesengesetzes",             # fremdes Gesetz (BGB § 310, echt)
    "§ 40a des Beurkundungsgesetzes",                          # fremdes Gesetz (BGB § 77, echt)
    "Artikel 246a § 1 Absatz 2 und 3 des Einführungsgesetzes",  # Artikel eines anderen Gesetzes (BGB § 312, echt)
])
def test_ignores_other_norms_and_foreign_laws(text):
    number = "1" if "§ 1" in text else ("40a" if "40a" in text else "536")
    assert not cites_number(text, number)
