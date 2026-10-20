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
