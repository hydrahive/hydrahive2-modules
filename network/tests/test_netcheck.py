"""Nur Geräte im eigenen Heimnetz (keine Anfragen ins Internet mit dem Schlüssel)."""
from __future__ import annotations

import pytest
from backend import netcheck
from backend.errors import NetError


@pytest.mark.parametrize("url,host,port", [
    ("https://192.168.178.1", "192.168.178.1", 443),
    ("https://192.168.178.1/", "192.168.178.1", 443),
    ("https://10.0.0.1:8443", "10.0.0.1", 8443),
    ("https://unifi.local", "unifi.local", 443),
])
def test_udm_adresse_gut(url, host, port):
    assert netcheck.udm_url(url) == (host, port)


@pytest.mark.parametrize("url,code", [
    ("http://192.168.178.1", "network_url_invalid"),
    ("192.168.178.1", "network_url_invalid"),
    ("https://192.168.178.1/pfad", "network_url_invalid"),
    ("https://user@192.168.178.1", "network_url_invalid"),
    ("https://8.8.8.8", "network_host_not_local"),
    ("https://example.com", "network_host_not_local"),
    ("https://127.0.0.1", "network_host_not_local"),
    ("https://169.254.1.1", "network_host_not_local"),
    ("", "network_url_invalid"),
])
def test_udm_adresse_schlecht(url, code):
    with pytest.raises(NetError) as e:
        netcheck.udm_url(url)
    assert e.value.code == code


@pytest.mark.parametrize("host,ok", [("192.168.3.1", True), ("fritz.box", True), ("172.16.0.1", True),
                                     ("1.2.3.4", False), ("fritz.box:49000", False), ("-x", False), ("", False),
                                     ("evil.com", False), ("fd00::1", True)])
def test_fritz_host(host, ok):
    if ok:
        assert netcheck.local_host(host) == host
    else:
        with pytest.raises(NetError):
            netcheck.local_host(host)
