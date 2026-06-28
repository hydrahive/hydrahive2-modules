"""Validator-Einheitstests — entity_id/domain/service-Regex."""
from __future__ import annotations

from backend import validators


def test_entity_ok():
    assert validators.is_entity("light.wohnzimmer")
    assert validators.is_entity("sensor.bad_temperatur")
    assert validators.is_entity("climate.flur_2")


def test_entity_bad():
    assert not validators.is_entity("light")            # kein Punkt
    assert not validators.is_entity("light.")           # leerer object-Teil
    assert not validators.is_entity(".wohnzimmer")      # leere domain
    assert not validators.is_entity("Light.Wohnzimmer") # Großbuchstaben
    assert not validators.is_entity("light.wohn zimmer")  # Leerzeichen
    assert not validators.is_entity("light.a.b")        # zwei Punkte
    assert not validators.is_entity("")                 # leer


def test_domain_ok_bad():
    assert validators.is_domain("light")
    assert validators.is_domain("input_boolean")
    assert not validators.is_domain("Light")
    assert not validators.is_domain("light.x")
    assert not validators.is_domain("")


def test_service_ok_bad():
    assert validators.is_service("turn_on")
    assert validators.is_service("set_temperature")
    assert not validators.is_service("turn-on")
    assert not validators.is_service("Turn_On")


def test_domain_of():
    assert validators.domain_of("light.wohnzimmer") == "light"
    assert validators.domain_of("invalid") == ""
