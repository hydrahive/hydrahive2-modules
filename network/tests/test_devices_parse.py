"""Geräte der Dream Machine lesen (echte, anonymisierte Antwort)."""
from __future__ import annotations

from backend import devices_parse as dp
from conftest_admin import FIX


def by_name(items, name, adopted=True):
    return next(d for d in items if d["name"] == name and d["adopted"] is adopted)


def test_vier_geraete_mit_art_und_zustand():
    items = dp.devices(FIX["device"])
    assert len(items) == 4
    gw = by_name(items, "Dream Machine Pro")
    assert (gw["kind"], gw["state"], gw["model"]) == ("gateway", "online", "UDMPRO")
    assert by_name(items, "FlexHD")["kind"] == "ap"
    assert by_name(items, "USW Lite 8 PoE")["kind"] == "switch"
    assert by_name(items, "USW Lite 8 PoE", adopted=False)["state"] == "pending"
    assert [d["kind"] for d in items] == ["gateway", "switch", "ap", "switch"]


def test_werte_des_gateways():
    gw = by_name(dp.devices(FIX["device"]), "Dream Machine Pro")
    assert gw["version"] == "5.1.34.34103" and gw["upgradable"] is False
    assert gw["uptime_s"] == 41055 and gw["clients"] == 42
    assert gw["cpu"] == 5.0 and gw["mem"] == 49.1
    assert {"name": "CPU", "value": 34.5} in gw["temps"]
    assert gw["tx_bytes"] == 65016436549


def test_ports_sortiert_mit_uplink_und_poe():
    sw = by_name(dp.devices(FIX["device"]), "USW Lite 8 PoE")
    assert [p["idx"] for p in sw["ports"]] == list(range(1, 9))
    p8 = sw["ports"][7]
    assert p8["uplink"] is True and p8["up"] is True and p8["speed"] == 1000
    p3 = sw["ports"][2]
    assert p3["up"] is False and p3["speed"] is None
    assert sw["ports"][0]["poe"] is False and sw["ports"][4]["poe"] is None
    gw = by_name(dp.devices(FIX["device"]), "Dream Machine Pro")
    assert [p["idx"] for p in gw["ports"]][:3] == [1, 2, 3] and gw["ports"][-1]["name"] == "SFP+ 2"
    assert gw["ports"][0]["errors"] == 2


def test_uplink_mit_name_des_geraets():
    items = dp.devices(FIX["device"])
    sw = by_name(items, "USW Lite 8 PoE")
    assert sw["uplink"] == {"mac": by_name(items, "Dream Machine Pro")["mac"], "name": "Dream Machine Pro", "port": 5,
                            "speed": 1000}


def test_funk_des_access_points():
    ap = by_name(dp.devices(FIX["device"]), "FlexHD")
    assert [r["band"] for r in ap["radios"]] == ["2.4", "5"]
    r24 = ap["radios"][0]
    assert (r24["channel"], r24["tx_power"], r24["utilization"], r24["clients"], r24["satisfaction"]) == (11, 17, 20, 10, 96)


def test_unbekannte_werte_leer():
    d = dp.devices({"data": [{"mac": "02:00:00:00:00:01", "type": "xyz", "state": 99}]})[0]
    assert d["kind"] == "other" and d["state"] == "unknown" and d["ports"] == [] and d["radios"] == []
    assert d["name"] == "02:00:00:00:00:01" and d["cpu"] is None and d["uplink"] is None
