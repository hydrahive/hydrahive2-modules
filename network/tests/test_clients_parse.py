"""Clients: aktive (stat/sta) + bekannte (rest/user), mit Verbindung zu Gerät/Port."""
from __future__ import annotations

from backend import clients_parse as cp
from backend import devices_parse as dp
from conftest_admin import FIX

DEVS = dp.devices(FIX["device"])


def items():
    return cp.clients(FIX["sta"], FIX["user"], DEVS)


def test_alle_bekannten_ohne_doppelte():
    rows = items()
    assert len(rows) == 71
    assert len({r["mac"] for r in rows}) == 71
    assert sum(1 for r in rows if r["online"]) == 42
    assert rows == sorted(rows, key=lambda r: (not r["online"], r["name"].lower()))


def test_wlan_client():
    mac = next(x["mac"] for x in FIX["sta"]["data"] if x.get("oui") == "Tuya Smart Inc." and x.get("ip") == "10.0.0.205")
    r = next(r for r in items() if r["mac"] == mac)
    assert r["online"] and not r["wired"] and r["band"] == "2.4" and r["signal"] == -70
    assert r["uplink_name"] == "FlexHD" and r["uplink_port"] is None and r["essid"] == "Heimnetz"
    assert (r["down_bytes"], r["up_bytes"]) == (117667, 925607)
    assert r["vendor"] == "Tuya Smart Inc." and r["satisfaction"] == 93


def test_kabel_client_mit_port():
    r = next(r for r in items() if r["ip"] == "10.0.0.214")
    assert r["online"] and r["wired"] and r["uplink_name"] == "Dream Machine Pro" and r["uplink_port"] == 1
    assert (r["down_bytes"], r["up_bytes"]) == (11539610, 7977160) and r["band"] is None


def test_offline_client():
    r = next(r for r in items() if r["ip"] == "10.0.0.54")
    assert not r["online"] and r["uplink_name"] == "FlexHD" and r["last_seen"] == 1793541456
    assert r["down_bytes"] is None


def test_name_ersatz():
    rows = cp.clients({"data": [{"mac": "02:00:00:00:ab:cd", "oui": "Acme", "is_wired": True}]}, {"data": []}, [])
    assert rows[0]["name"] == "Acme (ab:cd)"
    rows = cp.clients({"data": [{"mac": "02:00:00:00:ab:cd"}]}, {"data": [{"mac": "02:00:00:00:ab:cd", "name": "Drucker"}]}, [])
    assert rows[0]["name"] == "Drucker"
    assert cp.clients({"data": [{"mac": "02:00:00:00:ab:ce"}]}, {"data": []}, [])[0]["name"] == "02:00:00:00:ab:ce"


def test_eigener_name_vor_geraetename():
    rows = cp.clients({"data": [{"mac": "02:00:00:00:ab:cd", "hostname": "esp-1234", "name": None}]},
                      {"data": [{"mac": "02:00:00:00:ab:cd", "name": "Steckdose Flur"}]}, [])
    assert rows[0]["name"] == "Steckdose Flur"
