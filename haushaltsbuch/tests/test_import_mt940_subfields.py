"""MT940 Feld :86: mit ?-Subfeldern (Sparkasse/DK-Standard).

Befund 20.11.2026 (Tills echter Sparkassen-Export, 79 Zeilen): Name und
Verwendungszweck stehen in Subfeldern (?00 Buchungstext, ?20–?29 Verwendungszweck,
?30 BIC, ?31 IBAN, ?32/?33 Name). Der Parser las nur „NAME+“/„SVWZ+“ über
Leerzeichen-Grenzen, fand nichts und speicherte den ROHTEXT als Zweck, ohne
Gegenpartei. Folge: keine Händler-Erkennung, keine Kategorie-Vorschläge.
Felddefinition: kontopruef.de/mt940s.shtml (Feldschlüssel 00, 10, 20–29, 30–34, 60–63).
Testdaten erfunden, Aufbau wie Tills Datei.
"""
from __future__ import annotations

from backend.import_parsers import parse_import

MT940 = (
    ":20:STARTUMSE\r\n:25:12345678/0000000000\r\n:28C:00000/001\r\n:60F:C261101EUR1000,00\r\n"
    ":61:2611011101DR40,78N106NONREF\r\n"
    ":86:106?00KARTENZAHLUNG?109250?20SVWZ+2026-11-01T10.53?21Debitk.1 2028-12?22ABWA+LIDL SAGT DANKE/F\r\n"
    "rankfurt?30WELADEDDXXX?31DE00999999990000000001?32LIDL SAGT DANKE?34011\r\n"
    ":61:2611021102CR1833,60N166NONREF\r\n"
    ":86:166?00GUTSCHR. UEBERWEISUNG?109251?20EREF+855009339358?21SVWZ +Gehalt 11/2026?22 Abrechnung\r\n"
    "?30MARKDEF1760?31DE00888888880000000002?32Muster Arbeitgeber?33 GmbH\r\n"
    ":61:2611031103DR12,94N105NONREF\r\n"
    ":86:105?00FOLGELASTSCHRIFT?109250?20EREF+C9058469?21MREF+5681BECD?22CRED+DE00ZZZ00000000001?23SVWZ+Strom Nov\r\n"
    "?32Stadtwerke Beispiel\r\n"
    ":62F:C261103EUR2779,88\r\n"
).encode("cp1252")


def test_subfelder_liefern_name_zweck_iban_und_buchungstext():
    rows = parse_import(MT940, "mt940")
    assert [r.amount_minor for r in rows] == [-4078, 183360, -1294]
    lidl, gehalt, strom = rows
    assert lidl.counterparty == "LIDL SAGT DANKE"
    assert gehalt.counterparty == "Muster Arbeitgeber GmbH"          # ?32 + ?33 zusammengesetzt
    assert strom.counterparty == "Stadtwerke Beispiel"
    assert gehalt.purpose == "Gehalt 11/2026 Abrechnung"              # SVWZ aus ?2x zusammengesetzt
    assert strom.purpose == "Strom Nov"
    assert "?" not in (lidl.purpose or "") and "?2" not in (gehalt.purpose or "")
    assert gehalt.counterparty_identifier and gehalt.counterparty_identifier.endswith("0002")
    assert "DE00888888880000000002" != gehalt.counterparty_identifier  # maskiert, nicht im Klartext
    assert gehalt.bank_reference == "855009339358"                     # EREF aus Subfeldern
    assert lidl.category_hint == "KARTENZAHLUNG"                       # ?00 Buchungstext


def test_ohne_subfelder_bleibt_altes_verhalten():
    old = b":20:X\n:60F:C251230EUR0,00\n:61:2512310102D1,00NTRFNONREF//NONREF\n:86:SVWZ+Einkauf NAME+Laden\n:62F:D260102EUR1,00"
    row = parse_import(old, "mt940")[0]
    assert row.purpose == "Einkauf" and row.counterparty == "Laden"
