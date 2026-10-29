"""Adresse nur im Heimnetz; Schlüssel verschlüsselt und nie nach außen (SPEC.md „Einstellungen“)."""
from __future__ import annotations

import pytest
from backend import psk_crypto as tv_secrets
from backend import settings_store, validators


@pytest.mark.parametrize("addr", ["192.168.178.186", "10.0.0.5", "172.16.3.4", "fernseher.local", "bravia",
                                  "TV-Wohnzimmer.fritz.box", " 192.168.1.20 "])
def test_heimnetz_adressen_erlaubt(addr):
    assert validators.normalize_address(addr) == addr.strip().lower()


@pytest.mark.parametrize("addr", ["8.8.8.8", "1.1.1.1", "142.250.1.1", "example.com", "tv.hydrahive.de",
                                  "127.0.0.1", "localhost", "169.254.1.1", "0.0.0.0", "",
                                  "192.168.1.5:8080", "http://192.168.1.5", "192.168.1.5/sony", "a b", "x" * 300])
def test_andere_adressen_abgelehnt(addr):
    with pytest.raises(validators.AddressError):
        validators.normalize_address(addr)


def test_schluessel_verschluesselt_und_wieder_lesbar():
    sealed = tv_secrets.seal("geheim-psk-4711")
    assert sealed.startswith("tv:v1:") and "geheim" not in sealed
    assert tv_secrets.open_(sealed) == "geheim-psk-4711"
    assert tv_secrets.seal("geheim-psk-4711") != sealed      # neue Zufallszahl je Speichern


@pytest.mark.parametrize("bad", ["", "geheim", "tv:v1:", "tv:v1:!!!", "enc:v1:abc"])
def test_kaputter_schluessel_wird_abgelehnt(bad):
    with pytest.raises(tv_secrets.SecretError):
        tv_secrets.open_(bad)


@pytest.mark.parametrize("pos", [0, 5, 12, 20, -1])
def test_veraenderter_schluessel_wird_erkannt(pos):
    """Ein Byte des echten Inhalts kippen (nicht ein Füllzeichen der Base64-Form – das war zufällig wirkungslos)."""
    import base64
    sealed = tv_secrets.seal("abc")
    raw = bytearray(base64.urlsafe_b64decode(sealed[len(tv_secrets.PREFIX):] + "=="))
    raw[pos] ^= 0x01
    with pytest.raises(tv_secrets.SecretError):
        tv_secrets.open_(tv_secrets.PREFIX + base64.urlsafe_b64encode(bytes(raw)).decode())


def test_speichern_legt_keinen_klartext_ab():
    from hydrahive.db.connection import db
    settings_store.save(name="TV", address="192.168.178.186", psk="geheim-psk-4711", volume_limit=50, user="admin")
    with db() as conn:
        row = conn.execute("SELECT * FROM module_fernseher_settings").fetchone()
    assert "geheim-psk-4711" not in " ".join(str(v) for v in tuple(row))
    pub = settings_store.public()
    assert pub == {"configured": True, "name": "TV", "address": "192.168.178.186", "psk_set": True,
                   "volume_limit": 50}
    assert settings_store.connection() == ("192.168.178.186", "geheim-psk-4711")


def test_speichern_ohne_neuen_schluessel_behaelt_den_alten():
    settings_store.save(name="TV", address="192.168.178.186", psk="alt-1", volume_limit=60, user="admin")
    settings_store.save(name="TV 2", address="192.168.178.187", psk=None, volume_limit=40, user="admin")
    assert settings_store.connection() == ("192.168.178.187", "alt-1")
    assert settings_store.public()["name"] == "TV 2"


def test_nicht_eingerichtet():
    assert settings_store.public() == {"configured": False, "name": "", "address": "", "psk_set": False,
                                       "volume_limit": 60}
    assert settings_store.connection() is None


@pytest.mark.parametrize("limit", [0, 101, -5])
def test_lautstaerke_grenze_im_bereich(limit):
    with pytest.raises(ValueError):
        settings_store.save(name="TV", address="192.168.178.186", psk="x", volume_limit=limit, user="admin")
