"""Normbezeichnungen erkennen – Grundlage für exakte Suche (L1) und Zitat-Prüfer (L4)."""
from __future__ import annotations

import pytest
from backend.citation import Citation, parse_citation


@pytest.mark.parametrize("raw,abbr,enbez", [
    ("§ 536c BGB", "BGB", "§ 536c"),
    ("§536c BGB", "BGB", "§ 536c"),
    ("536c BGB", "BGB", "§ 536c"),
    ("BGB § 536c", "BGB", "§ 536c"),
    ("§ 536 c BGB", "BGB", "§ 536c"),
    ("§ 536C bgb", "BGB", "§ 536c"),
    ("§ 70 VwGO", "VwGO", "§ 70"),
    ("§ 67 OWiG", "OWiG", "§ 67"),
    ("§ 1 KSchG", "KSchG", "§ 1"),
    ("Art. 3 GG", "GG", "Art 3"),
    ("Art 3 GG", "GG", "Art 3"),
    ("§ 2 BetrKV", "BetrKV", "§ 2"),
    ("§ 34 SGB X", "SGB X", "§ 34"),
])
def test_recognises_common_forms(raw, abbr, enbez):
    known = {"BGB", "VwGO", "OWiG", "KSchG", "GG", "BetrKV", "SGB X"}
    assert parse_citation(raw, known) == Citation(abbr, enbez)


@pytest.mark.parametrize("raw", ["", "Mietminderung", "§ BGB", "§ 536c XYZ", "BGB", "536c"])
def test_not_a_citation(raw):
    assert parse_citation(raw, {"BGB"}) is None


def test_absatz_and_satz_are_ignored_for_lookup():
    assert parse_citation("§ 536 Abs. 1 S. 2 BGB", {"BGB"}) == Citation("BGB", "§ 536")
    assert parse_citation("§ 573c Absatz 1 BGB", {"BGB"}) == Citation("BGB", "§ 573c")


@pytest.mark.parametrize("raw,enbez,abbr", [
    ("§ 7 SGB II", "§ 7", "SGB 2"),
    ("§ 7 SGB 2", "§ 7", "SGB 2"),
    ("§ 1 SGB I", "§ 1", "SGB 1"),
    ("§ 27 SGB V", "§ 27", "SGB 5"),
    ("§ 14 SGB XI", "§ 14", "SGB 11"),
    ("§ 34 SGB X", "§ 34", "SGB X"),
    ("§ 34 SGB 10", "§ 34", "SGB X"),
    ("SGB XII § 19", "§ 19", "SGB 12"),
])
def test_sgb_roman_and_arabic_both_work(raw, enbez, abbr):
    """gesetze-im-internet: „SGB 1/2/5/8/11/12“ (arabisch), nur „SGB X“ römisch (Stand 20.10.2026).
    Zitiert wird meist römisch – beides muss auf das Kürzel im Korpus führen."""
    known = {"SGB 1", "SGB 2", "SGB 5", "SGB 8", "SGB 11", "SGB 12", "SGB X"}
    assert parse_citation(raw, known) == Citation(abbr, enbez)
