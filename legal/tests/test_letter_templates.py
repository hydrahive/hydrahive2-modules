"""Brief-Vorlagen (Plan L3 Schritt 3): Gerüst aus der Fallakte, Platzhalter sichtbar, Normen nur aus dem Korpus.

Wortlaut der verwendeten Normen am 20.10.2026 gegen den Live-Korpus (hydratest) geprüft: § 535, § 536, § 536c, § 286,
§ 543, § 568, § 573c, § 623 BGB, § 68/§ 70 VwGO, § 29 VwVfG, § 25 SGB X. SGG ist nicht im Korpus → keine SGG-Norm.
"""
from __future__ import annotations

from datetime import date

import pytest
from backend import citation, letter_templates

CORPUS = {"BGB", "VwGO", "VwVfG", "SGB X", "ZPO", "StPO", "GG"}
CASE = {"title": "Mietsache Hitze", "state": "NI", "their_ref": "Az. 12/345", "our_ref": "",
        "facts": "Seit Juni 2026 über 28 °C."}
ME = {"role": "me", "name": "Till Muster", "address": "Musterweg 1\n30159 Hannover"}
OPP = {"id": 7, "role": "opponent", "name": "Hausverwaltung Müller GmbH", "address": "Hauptstraße 1\n30159 Hannover"}


def test_six_templates_with_label_and_norms():
    keys = [t["key"] for t in letter_templates.list_templates()]
    assert keys == ["mangelanzeige", "mahnung", "widerspruch", "kuendigung", "akteneinsicht", "anwalt"]
    for t in letter_templates.list_templates():
        assert t["label"] and t["hint"]


@pytest.mark.parametrize("key", ["mangelanzeige", "mahnung", "widerspruch", "kuendigung", "akteneinsicht", "anwalt"])
def test_every_norm_in_every_template_is_in_the_corpus_list(key):
    d = letter_templates.draft(key, case=CASE, parties=[ME, OPP], recipient_id=7, today=date(2026, 10, 20))
    for f in citation.find_all(d["body"], CORPUS):
        assert f.unknown_law is None, f"{key}: unbekanntes Gesetz {f.raw}"


def test_mangelanzeige_filled_from_case():
    d = letter_templates.draft("mangelanzeige", case=CASE, parties=[ME, OPP], recipient_id=7, today=date(2026, 10, 20))
    assert d["sender"] == "Till Muster\nMusterweg 1\n30159 Hannover"
    assert d["recipient"] == "Hausverwaltung Müller GmbH\nHauptstraße 1\n30159 Hannover"
    assert d["date"] == "2026-10-20" and d["their_ref"] == "Az. 12/345"
    assert d["delivery"] == "einwurf_einschreiben" and d["letter_type"] == "mangelanzeige"
    assert "§ 536c BGB" in d["body"] and "Mangelanzeige" in d["subject"]
    assert "[" in d["body"], "Platzhalter für Fakten, die nur der Mensch kennt (Beschreibung, Frist-Datum)"
    assert "binnen" not in d["body"] and "innerhalb" not in d["body"], "Frist nur als Datum-Platzhalter"


def test_missing_me_or_recipient_gives_placeholders_not_crash():
    d = letter_templates.draft("mahnung", case=CASE, parties=[], recipient_id=None, today=date(2026, 10, 20))
    assert d["sender"].startswith("[") and d["recipient"].startswith("[")


def test_recipient_must_belong_to_case():
    with pytest.raises(letter_templates.TemplateError):
        letter_templates.draft("mahnung", case=CASE, parties=[ME, OPP], recipient_id=99, today=date(2026, 10, 20))


def test_unknown_template():
    with pytest.raises(letter_templates.TemplateError):
        letter_templates.draft("dsgvo", case=CASE, parties=[ME], recipient_id=None, today=date(2026, 10, 20))


def test_no_case_data_leaks_into_other_fields():
    """Sachverhalt geht nur ins Anwaltsschreiben, nicht in Briefe an die Gegenseite."""
    d = letter_templates.draft("mangelanzeige", case=CASE, parties=[ME, OPP], recipient_id=7, today=date(2026, 10, 20))
    assert "28 °C" not in d["body"]
    d = letter_templates.draft("anwalt", case=CASE, parties=[ME, OPP], recipient_id=7, today=date(2026, 10, 20))
    assert "28 °C" in d["body"]


# Am 20.10.2026 im Live-Korpus gelesen (Wortlaut + Titel), siehe Modul-Docstring.
VERIFIED = {("BGB", "§ 535"), ("BGB", "§ 536"), ("BGB", "§ 536c"), ("BGB", "§ 286"), ("BGB", "§ 543"), ("BGB", "§ 568"),
            ("BGB", "§ 573c"), ("BGB", "§ 623"), ("VwGO", "§ 68"), ("VwGO", "§ 70"), ("VwVfG", "§ 29"), ("SGB X", "§ 25")}


def test_templates_only_use_verified_norms():
    used = set()
    for key in letter_templates.ORDER:
        d = letter_templates.draft(key, case=CASE, parties=[ME, OPP], recipient_id=7, today=date(2026, 10, 20))
        for text in (d["body"], d["subject"]):
            used |= {(c.abbr, c.enbez) for f in citation.find_all(text, CORPUS) for c in f.citations}
    assert used and used <= VERIFIED, used - VERIFIED
