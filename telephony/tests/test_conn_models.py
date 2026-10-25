"""Eingaben der SIP-Verbindung und Heimnetz-Prüfung (PLAN-EINSTELLUNGEN „Felder“, SPEC-V1 §16.4)."""
from __future__ import annotations

import ipaddress

import pytest
from pydantic import ValidationError


def _valid(**over) -> dict:
    d = {"pbx": "fritzbox", "display_name": "HydraHive", "registrar": "fritz.box", "registrar_port": 5060,
         "username": "hydra-telefon", "password": "Sehr-Geheim-42", "own_number": "+49 30 1234567",
         "local_sip_port": 5070, "rtp_port_min": 7078, "rtp_port_max": 7109, "register_interval": 300}
    d.update(over)
    return d


def test_gueltige_eingabe_mit_standardwerten() -> None:
    from backend.conn_models import ConnectionIn

    m = ConnectionIn(registrar="fritz.box", username="hydra-telefon", password="Sehr-Geheim-42")
    assert (m.pbx, m.registrar_port, m.local_sip_port, m.rtp_port_min, m.rtp_port_max, m.register_interval) == \
        ("fritzbox", 5060, 5070, 7078, 7109, 300)
    assert m.display_name == "HydraHive"


def test_kennwort_erscheint_nie_in_ausgabe_oder_repr() -> None:
    from backend.conn_models import ConnectionIn

    m = ConnectionIn(**_valid())
    assert "Sehr-Geheim-42" not in repr(m) and "Sehr-Geheim-42" not in str(m.model_dump())


@pytest.mark.parametrize("field,value", [
    ("pbx", "asterisk-cloud"),
    ("registrar", ""), ("registrar", "fritz box"), ("registrar", "a" * 254), ("registrar", "http://fritz.box"),
    ("registrar_port", 0), ("registrar_port", 70000),
    ("username", ""), ("username", "a b"), ("username", "x" * 129),
    ("own_number", "abc"), ("own_number", "1" * 40),
    ("local_sip_port", 80), ("local_sip_port", 70000),
    ("rtp_port_min", 7079),            # ungerade: RTP braucht gerade Ports (RTCP = +1)
    ("rtp_port_max", 7070),            # kleiner als min
    ("rtp_port_max", 9100),            # Bereich zu groß
    ("register_interval", 30), ("register_interval", 4000),
    ("display_name", "x" * 81), ("display_name", "a\r\nVia: evil"), ("display_name", 'Hydra" <sip:x@y>'),
    ("display_name", "a<b"), ("display_name", "a\\b"), ("display_name", "a\tb"),
])
def test_ungueltige_eingaben(field: str, value) -> None:
    from backend.conn_models import ConnectionIn

    with pytest.raises(ValidationError):
        ConnectionIn(**_valid(**{field: value}))


def test_fritzbox_braucht_8_zeichen_benutzer_und_kennwort() -> None:
    from backend.conn_models import ConnectionIn

    with pytest.raises(ValidationError):
        ConnectionIn(**_valid(username="kurz"))
    with pytest.raises(ValidationError):
        ConnectionIn(**_valid(password="kurz"))
    # andere Anlagen: eigene Regeln, nur nicht leer
    ConnectionIn(**_valid(pbx="sip", username="1001", password="1234"))


def test_lokaler_sip_port_nicht_im_sprachbereich() -> None:
    from backend.conn_models import ConnectionIn

    with pytest.raises(ValidationError):
        ConnectionIn(**_valid(local_sip_port=7080))


def test_kennwort_beim_aendern_optional() -> None:
    from backend.conn_models import ConnectionIn

    m = ConnectionIn(**_valid(password=None))
    assert m.password is None


# ---- Heimnetz-Prüfung ----

def _res(*ips):
    return lambda host: list(ips)


@pytest.mark.parametrize("host,ips", [
    ("192.168.178.1", ()), ("10.0.0.5", ()), ("172.16.3.1", ()),
    ("fritz.box", ("192.168.178.1",)),
])
def test_heimnetz_erlaubt(host: str, ips) -> None:
    from backend import netguard

    ip = netguard.check(host, resolve=_res(*ips))
    assert ipaddress.ip_address(ip).is_private


@pytest.mark.parametrize("host,ips", [
    ("8.8.8.8", ()), ("127.0.0.1", ()), ("169.254.1.1", ()), ("0.0.0.0", ()), ("100.64.0.1", ()),
    ("224.0.0.1", ()), ("::1", ()), ("fe80::1", ()),
    ("sip.example.org", ("93.184.216.34",)),
    ("fritz.box", ("192.168.178.1", "8.8.8.8")),       # gemischt: abgelehnt
    ("nichtda.lan", ()),                               # nicht auflösbar
])
def test_nicht_heimnetz_abgelehnt(host: str, ips) -> None:
    from backend import netguard

    with pytest.raises(netguard.Blocked):
        netguard.check(host, resolve=_res(*ips))


def test_aufloesungsfehler_wird_blocked() -> None:
    from backend import netguard

    def boom(host):
        raise OSError("dns kaputt")
    with pytest.raises(netguard.Blocked):
        netguard.check("fritz.box", resolve=boom)
