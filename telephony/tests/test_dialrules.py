"""Nummernregeln für ausgehende Anrufe (PLAN-ANRUFEN-3, Sicherheit Punkt 2).

Nur Platzhalter-Nummern. Achtung: „0123 …“ ist kein neutraler Platzhalter – 012 ist der Bereich „Innovative Dienste“
und wird zu Recht als Sondernummer gesperrt. Deshalb hier 030 1234567.
"""
from __future__ import annotations

import pytest
from backend import dialrules


def ok(number: str, **kw) -> str:
    return dialrules.check(number, **kw)


def blocked(number: str, **kw) -> str:
    with pytest.raises(dialrules.Blocked) as e:
        dialrules.check(number, **kw)
    return e.value.code


@pytest.mark.parametrize("raw, norm", [
    ("030 1234567", "0301234567"),
    ("030/12 34-567", "0301234567"),
    ("(030) 1234567", "0301234567"),
    ("+49 30 1234567", "0301234567"),
    ("0049 30 1234567", "0301234567"),
    ("0151 23456789", "015123456789"),
    ("0171-2345678", "01712345678"),
])
def test_deutsche_nummern_erlaubt_und_normalisiert(raw: str, norm: str) -> None:
    assert ok(raw) == norm


@pytest.mark.parametrize("number", ["110", "112", " 1 1 2 ", "+49112", "0049110", "115", "116116", "116117",
                                    "0112", "0110"])
def test_notruf_und_behoerden_nie(number: str) -> None:
    assert blocked(number, allow_premium=True, allow_foreign=True) == "emergency"


@pytest.mark.parametrize("number", ["**610", "#96*5*", "*31#", "030*123456", "030123#", "**9"])
def test_steuercodes_nie(number: str) -> None:
    assert blocked(number, allow_premium=True, allow_foreign=True) == "invalid"


@pytest.mark.parametrize("number", ["0900 1234567", "0137 1234567", "0138 123456", "0180 5123456", "0181 1234",
                                    "0190 123456", "11833", "0118 33", "012 3456789", "032 12345678",
                                    "+881 12345678", "0088 112345678"])
def test_premium_nur_mit_freigabe(number: str) -> None:
    assert blocked(number) == "premium"
    assert blocked(number, allow_foreign=True) == "premium"


def test_premium_mit_freigabe() -> None:
    assert ok("0900 1234567", allow_premium=True) == "09001234567"
    assert ok("11833", allow_premium=True) == "11833"


@pytest.mark.parametrize("number", ["0043 1 2345678", "+43 1 2345678", "+1 555 0100", "00 1 555 0100"])
def test_ausland_nur_mit_freigabe(number: str) -> None:
    assert blocked(number) == "foreign"
    assert blocked(number, allow_premium=True) == "foreign"


def test_ausland_mit_freigabe_bleibt_international() -> None:
    assert ok("+43 1 2345678", allow_foreign=True) == "004312345678"
    assert ok("0043 1 2345678", allow_foreign=True) == "004312345678"


def test_satellit_bleibt_premium_auch_mit_auslandsfreigabe() -> None:
    assert blocked("+881 12345678", allow_foreign=True) == "premium"
    assert ok("+881 12345678", allow_foreign=True, allow_premium=True) == "0088112345678"


@pytest.mark.parametrize("number", ["", "  ", "12", "abc", "030 1234a67", "030..123456", "+", "++49123456",
                                    "0" * 21, "01234567890123456789012", "030\n1234567", "030;tag=x", "sip:0301234567@x"])
def test_kaputte_eingaben(number: str) -> None:
    assert blocked(number, allow_premium=True, allow_foreign=True) == "invalid"


@pytest.mark.parametrize("number", ["456789", "2345678"])
def test_ohne_vorwahl_abgelehnt(number: str) -> None:
    assert blocked(number, allow_premium=True, allow_foreign=True) == "no_area_code"


def test_ergebnis_nur_ziffern() -> None:
    for n in ["030 1234567", "+49 30 1234567", "0151 23456789"]:
        assert ok(n).isdigit()


def test_maskieren() -> None:
    assert dialrules.mask("0301234567") == "•••567"
    assert dialrules.mask("12") == "unbekannt"
