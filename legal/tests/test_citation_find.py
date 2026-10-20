"""Normen in Fließtext finden (Plan L3 Schritt 1) – Grundlage für Prüfliste und Markierung im Brief-Editor.

find_all(text, known) liefert je Fund: Original-Ausschnitt, Position (start/end im Text) und die Citation, die
parse_citation dafür liefern würde. Nur Funde mit bekanntem Gesetz – „§ 536c XYZ“ ist kein Fund (dafür gibt es die
Kategorie „Gesetz unbekannt“, siehe test_unknown_law_is_reported).
"""
from __future__ import annotations

import pytest
from backend.citation import Citation, find_all

KNOWN = {"BGB", "GG", "VwGO", "SGB 2", "SGB X", "BetrKV", "ZPO"}


def _cits(text):
    return [(c.abbr, c.enbez) for f in find_all(text, KNOWN) for c in f.citations]


@pytest.mark.parametrize("text,expected", [
    ("Gemäß § 536c BGB zeige ich den Mangel an.", [("BGB", "§ 536c")]),
    ("nach § 536 Abs. 1 S. 2 BGB ist die Miete gemindert", [("BGB", "§ 536")]),
    ("§§ 535 ff. BGB", [("BGB", "§ 535")]),
    ("§§ 536, 536c BGB", [("BGB", "§ 536"), ("BGB", "§ 536c")]),
    ("§§ 536 und 536c BGB", [("BGB", "§ 536"), ("BGB", "§ 536c")]),
    ("§§ 535 bis 536c BGB", [("BGB", "§ 535"), ("BGB", "§ 536c")]),
    ("Art. 3 Abs. 1 GG und § 70 VwGO", [("GG", "Art 3"), ("VwGO", "§ 70")]),
    ("§ 7 SGB II, § 34 SGB X", [("SGB 2", "§ 7"), ("SGB X", "§ 34")]),
    ("(§ 536c BGB)", [("BGB", "§ 536c")]),
    ("§ 536c BGB.", [("BGB", "§ 536c")]),
    ("§536c BGB;§ 2 BetrKV", [("BGB", "§ 536c"), ("BetrKV", "§ 2")]),
    ("Siehe § 536c\nBGB", [("BGB", "§ 536c")]),
    ("Der Paragraph § regelt nichts.", []),
    ("Mietminderung ohne Norm", []),
    ("§ 536c ohne Gesetz", []),
    ("Telefon 0511 536 BGB-Gesellschaft", []),
])
def test_finds_citations_in_text(text, expected):
    assert _cits(text) == expected


def test_positions_point_to_the_original_text():
    text = "Hiermit zeige ich gemäß § 536c BGB an, dass – vgl. auch §§ 535, 536 BGB – die Wohnung zu heiß ist."
    found = find_all(text, KNOWN)
    assert [text[f.start:f.end] for f in found] == ["§ 536c BGB", "§§ 535, 536 BGB"]
    assert [f.raw for f in found] == ["§ 536c BGB", "§§ 535, 536 BGB"]
    assert [len(f.citations) for f in found] == [1, 2]


def test_unknown_law_is_reported():
    """Gesetz nicht im Korpus → Fund mit citation=None, damit die Prüfliste es rot zeigen kann."""
    found = find_all("Nach § 5 WiStG ist das verboten, siehe auch § 536c BGB.", KNOWN)
    assert [(f.raw, f.citation) for f in found] == [("§ 5 WiStG", None), ("§ 536c BGB", Citation("BGB", "§ 536c"))]
    assert found[0].unknown_law == "WiStG"


def test_same_norm_twice_two_findings():
    found = find_all("§ 536c BGB … nochmals § 536c BGB", KNOWN)
    assert len(found) == 2 and found[0].start < found[1].start


def test_no_runaway_on_long_text():
    text = ("Wort " * 20000) + "§ 536c BGB"
    assert _cits(text) == [("BGB", "§ 536c")]
