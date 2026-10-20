"""Parser für gesetze-im-internet.de-XML (gii-norm.dtd 1.01). Fixtures = echte Ausschnitte vom 20.10.2026."""
from __future__ import annotations

from conftest import fixture_xml

from backend.gii_parse import parse_law


def _by(norms, enbez):
    return next(n for n in norms if n.enbez == enbez)


def test_bgb_head_and_norms():
    law = parse_law("bgb", fixture_xml("bgb"))
    assert law.key == "bgb"
    assert law.abbr == "BGB"
    assert law.title == "Bürgerliches Gesetzbuch"
    assert "Neugefasst durch Bek. v. 2.1.2002" in law.stand
    n = _by(law.norms, "§ 536c")
    assert n.title == "Während der Mietzeit auftretende Mängel; Mängelanzeige durch den Mieter"
    assert n.text.startswith("(1) Zeigt sich im Laufe der Mietzeit ein Mangel der Mietsache")
    assert "(2) Unterlässt der Mieter die Anzeige" in n.text


def test_paragraphs_and_lists_keep_line_breaks():
    n = _by(parse_law("bgb", fixture_xml("bgb")).norms, "§ 536c")
    lines = n.text.split("\n")
    assert any(line.startswith("(2) ") for line in lines)
    assert "1. die in § 536 bestimmten Rechte geltend zu machen," in lines
    assert "3. ohne Bestimmung einer angemessenen Frist zur Abhilfe nach § 543 Abs. 3 Satz 1 zu kündigen." in lines
    assert "  " not in n.text


def test_skips_table_of_contents_and_repealed_norms():
    enbez = [n.enbez for n in parse_law("bgb", fixture_xml("bgb")).norms]
    assert "Inhaltsübersicht" not in enbez
    assert "§ 10" not in enbez                       # (weggefallen)
    assert enbez.count("§ 536c") == 1


def test_order_follows_document():
    enbez = [n.enbez for n in parse_law("bgb", fixture_xml("bgb")).norms]
    assert enbez.index("§ 535") < enbez.index("§ 536") < enbez.index("§ 536c") < enbez.index("§ 1601")


def test_amtabk_wins_over_jurabk():
    """L0: jurabk ist „OWiG 1968“, zitiert wird „OWiG“ (amtabk)."""
    law = parse_law("owig_1968", fixture_xml("owig_1968"))
    assert law.abbr == "OWiG"
    assert {n.abbr for n in law.norms} == {"OWiG"}


def test_gliederung_is_inherited():
    """VwGO § 70 hat keine Überschrift – die Gliederung trägt die Suche (L0 §6a)."""
    n = _by(parse_law("vwgo", fixture_xml("vwgo")).norms, "§ 70")
    assert n.title == ""
    assert "Besondere Vorschriften für Anfechtungs- und Verpflichtungsklagen" in n.gliederung
    assert n.text.startswith("(1) Der Widerspruch ist innerhalb eines Monats")


def test_betrkv_long_catalogue_complete():
    n = _by(parse_law("betrkv", fixture_xml("betrkv")).norms, "§ 2")
    assert n.title == "Aufstellung der Betriebskosten"
    assert "Grundsteuer" in n.text
    assert len(n.text) > 5000


def test_norm_id_is_stable():
    a = _by(parse_law("bgb", fixture_xml("bgb")).norms, "§ 536c")
    b = _by(parse_law("bgb", fixture_xml("bgb")).norms, "§ 536c")
    assert a.doknr == b.doknr == "BJNR001950896BJNE245702377"


def test_broken_xml_is_a_clear_error():
    import pytest
    from backend.gii_parse import GiiParseError
    with pytest.raises(GiiParseError):
        parse_law("bgb", b"<dokumente><norm>kaputt")
    with pytest.raises(GiiParseError):
        parse_law("bgb", b"<dokumente></dokumente>")      # kein einziges Gesetz-Kopf
