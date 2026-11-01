"""Zugänge aus dem Safe: richtige Art, nie der Wert nach außen."""
from __future__ import annotations

import pytest
from backend import creds
from backend.errors import NetError


def test_schluessel_und_login(safe):
    assert creds.udm_key("boss", "udm") == "geheimer-UDM-Schluessel-123"
    assert creds.fritz_login("boss", "fritz") == ("hydra", "fritz-Passwort-9")


@pytest.mark.parametrize("name", ["fritz", "gibtsnicht", "", None])
def test_kein_schluessel(safe, name):
    with pytest.raises(NetError) as e:
        creds.udm_key("boss", name)
    assert e.value.code == "network_credential_invalid"


def test_leerer_schluessel(safe):
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import delete_credential, save_credential
    ok, _ = save_credential("boss", Credential(name="leer", type="header", value="", header_name="X-API-KEY"))
    try:
        if ok:
            with pytest.raises(NetError):
                creds.udm_key("boss", "leer")
    finally:
        delete_credential("boss", "leer")


def test_anderer_nutzer_sieht_nichts(safe):
    with pytest.raises(NetError):
        creds.udm_key("testuser", "udm")
    assert creds.names("testuser") == []


def test_namen_ohne_werte(safe):
    names = creds.names("boss")
    assert {n["name"] for n in names} >= {"udm", "fritz"}
    assert all(set(n) == {"name", "type", "url_pattern"} for n in names)
    assert "geheimer" not in str(names)
