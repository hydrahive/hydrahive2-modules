"""M2 Schritt 1: Empfänger prüfen – gültige Adressen, Namen mit Umlauten, keine Kopfzeilen-Injektion, Grenzen."""
from __future__ import annotations

import pytest


def test_einfach_und_mit_namen():
    from backend import addresses
    r = addresses.parse_list("anna@example.org, Jürgen Müller <j@example.de>; \"Müller, Jürgen\" <jm@example.de>")
    assert [(a.name, a.addr) for a in r] == [("", "anna@example.org"), ("Jürgen Müller", "j@example.de"),
                                            ("Müller, Jürgen", "jm@example.de")]


def test_doppelte_weg_reihenfolge_bleibt():
    from backend import addresses
    r = addresses.parse_list("a@x.de, B <b@x.de>, A@X.de, b@x.de")
    assert [a.addr for a in r] == ["a@x.de", "b@x.de"]


@pytest.mark.parametrize("bad", ["kaputt", "a@", "@x.de", "a@x", "a b@x.de", "<>", "a@x.de>", "a@@x.de", "a@x..de",
                                 "x" * 65 + "@x.de"])
def test_ungueltig(bad):
    from backend import addresses
    with pytest.raises(addresses.AddressError):
        addresses.parse_list(bad)


@pytest.mark.parametrize("evil", ["a@x.de\r\nBcc: opfer@x.de", "a@x.de\nSubject: x", "Name\r\nX-Evil: 1 <a@x.de>",
                                  "a@x.de\x00", "\"x\r\n\" <a@x.de>", "a@x.de\rBcc: b@x.de"])
def test_keine_kopfzeilen_injektion(evil):
    from backend import addresses
    with pytest.raises(addresses.AddressError):
        addresses.parse_list(evil)


def test_hoechstens_100():
    from backend import addresses
    addresses.parse_list(", ".join(f"a{i}@x.de" for i in range(100)))
    with pytest.raises(addresses.AddressError):
        addresses.parse_list(", ".join(f"a{i}@x.de" for i in range(101)))


def test_leer_ist_leer():
    from backend import addresses
    assert addresses.parse_list("") == [] and addresses.parse_list("  ,  ;  ") == []


def test_kopfzeile_kodiert_umlaute():
    """Für den Kopf: Name nach RFC 2047, Adresse roh; nie ein Zeilenumbruch."""
    from backend import addresses
    h = addresses.header(addresses.parse_list("Jürgen Müller <j@example.de>, plain@x.de"))
    assert "j@example.de" in h and "plain@x.de" in h and "\n" not in h and "\r" not in h
    from email.header import decode_header, make_header
    assert "Jürgen Müller" in str(make_header(decode_header(h)))


def test_name_mit_sonderzeichen_wird_quotiert():
    from backend import addresses
    h = addresses.header(addresses.parse_list('"Müller, Jürgen" <jm@example.de>'))
    from email.utils import getaddresses
    assert getaddresses([h])[0][1] == "jm@example.de"
    from email.header import decode_header, make_header
    assert "Müller, Jürgen" in str(make_header(decode_header(h)))


def test_eigene_adresse_entfernen():
    from backend import addresses
    r = addresses.without(addresses.parse_list("Till <TILL@example.net>, a@x.de"), "till@example.net")
    assert [a.addr for a in r] == ["a@x.de"]


@pytest.mark.parametrize("evil", ["a@x.de\r\nBcc: opfer@x.de", "a@x.de\nb@x.de", "a@x.de\x00", "Name\r\n <a@x.de>"])
def test_erste_schicht_fehlermeldung(evil):
    """Die erste Prüfung (CR/LF/NUL) greift selbst – nicht erst eine spätere Zufalls-Ablehnung."""
    from backend import addresses
    with pytest.raises(addresses.AddressError, match="Zeilenumbruch oder Nullzeichen"):
        addresses.parse_list(evil)


@pytest.mark.parametrize("bad", ["Name <a@x.de> <b@x.de>", "<a@x.de", "Name a@x.de>", "a<b>@x.de", "Name <<a@x.de>>"])
def test_spitze_klammern(bad):
    from backend import addresses
    with pytest.raises(addresses.AddressError):
        addresses.parse_list(bad)
