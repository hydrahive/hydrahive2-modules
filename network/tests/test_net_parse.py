"""Netz: Aufbau als Baum, Netze, WLANs (ohne Passwort), Portfreigaben."""
from __future__ import annotations

from backend import net_parse as npx
from conftest_admin import FIX


def test_baum_ab_dream_machine():
    roots = npx.tree(FIX["topology"])
    gw = next(r for r in roots if r["name"] == "Dream Machine Pro")
    names = [c["name"] for c in gw["children"]]
    assert "USW Lite 8 PoE" in names and gw["kind"] == "device" and gw["model"] == "UDMPRO"

    def count(n):
        return 1 + sum(count(c) for c in n["children"])
    assert sum(count(r) for r in roots) == 46
    assert all(c["kind"] in ("device", "client") for c in gw["children"])
    wl = [n for r in roots for n in _walk(r) if n["link"] == "wireless"]
    assert len(wl) == 20 and all(n["kind"] == "client" for n in wl)
    ap = next(n for r in roots for n in _walk(r) if n["name"] == "FlexHD")
    assert len([c for c in ap["children"] if c["link"] == "wireless"]) == 20


def _walk(n):
    yield n
    for c in n["children"]:
        yield from _walk(c)


def test_baum_ohne_schleifen():
    topo = {"vertices": [{"mac": "a", "name": "A", "type": "DEVICE"}, {"mac": "b", "name": "B", "type": "DEVICE"}],
            "edges": [{"uplinkMac": "a", "downlinkMac": "b", "type": "WIRED"}, {"uplinkMac": "b", "downlinkMac": "a", "type": "WIRED"}]}
    roots = npx.tree(topo)
    assert len(roots) == 1 and roots[0]["children"][0]["children"] == []


def test_netze_wlans_freigaben():
    n = npx.net(FIX["networkconf"], FIX["wlanconf"], FIX["portforward"], {"data": [1, 2]}, {"data": []})
    lan = next(x for x in n["networks"] if x["purpose"] == "corporate")
    assert lan == {"name": "Default", "purpose": "corporate", "vlan": None, "subnet": "10.0.0.1/24",
                   "dhcp": {"on": True, "start": "10.0.0.6", "stop": "10.0.0.254"}}
    assert sum(1 for x in n["networks"] if x["purpose"] == "wan") == 2
    w = n["wlans"][0]
    assert w == {"name": "Heimnetz", "enabled": True, "security": "wpapsk", "wpa_mode": "wpa2", "bands": ["2g", "5g"],
                 "guest": False, "hidden": False, "network": "Default"}
    assert n["forwards"] == [{"name": "plex", "enabled": True, "proto": "tcp_udp", "port": "32400", "to_ip": "10.0.0.3",
                              "to_port": "32400"}]
    assert (n["firewall_rules"], n["routes"]) == (2, 0)
