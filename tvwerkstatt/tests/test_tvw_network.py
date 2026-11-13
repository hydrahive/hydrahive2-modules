"""Baustein 2: eigenes Netz hhtvw0 + Sperrliste hhtvw-acl, Ausnahme je Fernseher nur für seinen ADB-Port.

incus ist die FakeIncus-Attrappe. Kein echter Container in der Unit-Suite. Die echte Messung steht in PLAN-E1.md.
"""
from __future__ import annotations

import asyncio
import ipaddress

import pytest
from backend import network

TV = ("192.168.178.200", 5555)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def no_host(monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "203.0.113.9/32"})


def _egress(fake):
    return fake.acls[network.ACL]["egress"]


def _same(have, want) -> bool:
    """Reihenfolge egal (incus wertet reject vor allow), Inhalt genau gleich."""
    from backend import netrules
    return len(have) == len(want) and netrules.same(have, want)


def _reject_all(fake) -> list[str]:
    return [r for r in _egress(fake) if r["action"] == "reject" and "protocol" not in r]


def _covered(addr: str, dest: str) -> bool:
    ip = ipaddress.ip_address(addr)
    return any(ip in ipaddress.ip_network(d) for d in dest.split(",") if d and ":" not in d)


# --- Namen und Teilnetze --------------------------------------------------------------------------------------

def test_eigene_namen():
    assert network.NET == "hhtvw0" and network.ACL == "hhtvw-acl"
    assert network.NET not in ("hhnat0", "hhvibe0", "hhlabor0")


def test_teilnetze_ueberschneiden_sich_nicht_mit_vibe_labor_und_nat():
    belegt = [ipaddress.ip_network(n) for n in ("10.79.0.0/24", "10.80.0.0/24", "172.31.79.0/24", "10.77.0.0/24",
                                                "10.78.0.0/24", "172.31.77.0/24", "10.10.0.0/24")]
    for c in network._CANDIDATES:
        assert not any(ipaddress.ip_network(c).overlaps(b) for b in belegt), c


def test_freies_teilnetz_aus_vorrat(monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: {network._CANDIDATES[0]})
    assert network.choose_subnet() == network._CANDIDATES[1]


def test_alle_teilnetze_belegt(monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set(network._CANDIDATES))
    with pytest.raises(network.TvwNetworkError) as e:
        network.choose_subnet()
    assert e.value.code == "tvw_subnet_unavailable"


# --- Regeln: rein berechnet -----------------------------------------------------------------------------------

def test_ohne_fernseher_alles_private_gesperrt(no_host):
    rules = network.rules([])
    reject = [r for r in rules if r["action"] == "reject"]
    assert len(reject) == 1 and rules[-1] == {"action": "allow", "state": "enabled"}
    for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "169.254.0.0/16", "127.0.0.0/8",
                "fc00::/7", "fe80::/10", "192.168.178.2/32", "203.0.113.9/32"):
        assert net in reject[0]["destination"].split(",")


def test_fernseher_wird_aus_den_gesperrten_bereichen_herausgerechnet(no_host):
    dest = [r for r in network.rules([TV]) if r["action"] == "reject" and "protocol" not in r][0]["destination"]
    assert not _covered(TV[0], dest)
    for andere in ("192.168.178.199", "192.168.178.201", "192.168.178.1", "192.168.178.3", "192.168.0.1", "10.1.2.3"):
        assert _covered(andere, dest), andere


def test_am_fernseher_ist_nur_der_adb_port_offen(no_host):
    tv = [r for r in network.rules([TV]) if r.get("destination") == f"{TV[0]}/32"]
    assert {r["protocol"] for r in tv} == {"tcp", "udp", "icmp4"}
    assert all(r["action"] == "reject" and r["state"] == "enabled" for r in tv)
    tcp = next(r for r in tv if r["protocol"] == "tcp")
    assert tcp["destination_port"] == "1-5554,5556-65535"
    assert "destination_port" not in next(r for r in tv if r["protocol"] == "udp")


@pytest.mark.parametrize("port,erwartet", [(1, "2-65535"), (65535, "1-65534"), (37000, "1-36999,37001-65535")])
def test_portbereiche_an_den_raendern(no_host, port, erwartet):
    tcp = [r for r in network.rules([("192.168.178.200", port)]) if r.get("protocol") == "tcp"][0]
    assert tcp["destination_port"] == erwartet


def test_zwei_fernseher(no_host):
    rules = network.rules([TV, ("192.168.178.201", 41234)])
    dest = [r for r in rules if r["action"] == "reject" and "protocol" not in r][0]["destination"]
    assert not _covered("192.168.178.200", dest) and not _covered("192.168.178.201", dest)
    assert len([r for r in rules if r.get("protocol") == "tcp"]) == 2


@pytest.mark.parametrize("bad", ["8.8.8.8", "127.0.0.1", "169.254.1.1", "192.168.178.2", "fe80::1", "kein", "",
                                 "192.168.178.0/24"])
def test_ungueltige_fernseher_adresse(no_host, bad):
    with pytest.raises(network.TvwNetworkError) as e:
        network.rules([(bad, 5555)])
    assert e.value.code == "tvw_bad_address"


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_ungueltiger_port(no_host, port):
    with pytest.raises(network.TvwNetworkError) as e:
        network.rules([("192.168.178.200", port)])
    assert e.value.code == "tvw_bad_address"


# --- Netz anlegen, Regeln nachziehen --------------------------------------------------------------------------

def test_netz_und_sperrliste_in_richtiger_reihenfolge(fake_incus, no_host):
    run(network.ensure_network([TV]))
    calls = [" ".join(c) for c in fake_incus.calls]
    created = next(c for c in calls if c.startswith(f"network create {network.NET}"))
    assert calls.index(f"network acl create {network.ACL}") < calls.index(created)
    assert "ipv4.nat=true" in created and "ipv6.address=none" in created
    assert "raw.dnsmasq" not in created                    # Fund Probelauf: ohne Namensdienst löst nichts auf
    assert calls.index(created) < calls.index(f"network set {network.NET} security.acls={network.ACL}")
    assert _same(_egress(fake_incus), network.rules([TV]))


def test_netz_idempotent(fake_incus, no_host):
    run(network.ensure_network([TV]))
    vorher = len(fake_incus.calls)
    run(network.ensure_network([TV]))
    neu = [" ".join(c) for c in fake_incus.calls[vorher:]]
    assert not [c for c in neu if " create " in f" {c} " or "rule add" in c or "rule remove" in c], neu


@pytest.mark.parametrize("stelle", ["network acl create", "network acl rule add", "network create", "network set"])
def test_incus_fehler_bricht_ab(fake_incus, no_host, stelle):
    fake_incus.fail[stelle] = "boom"
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.ensure_network([TV]))
    assert e.value.code == "tvw_incus_failed"


def test_fernseher_dazu_und_wieder_weg(fake_incus, no_host):
    run(network.ensure_network([]))
    assert run(network.sync_rules([TV])) is True
    assert _same(_egress(fake_incus), network.rules([TV]))
    assert run(network.sync_rules([TV])) is False
    assert run(network.sync_rules([])) is True
    assert _same(_egress(fake_incus), network.rules([]))


def test_beim_nachziehen_nie_ohne_sperre(fake_incus, no_host):
    """Erst die neuen Regeln, dann die alten weg: Zu jedem Zeitpunkt steht eine Sperre für alles Private."""
    run(network.ensure_network([]))
    vorher = len(fake_incus.calls)
    run(network.sync_rules([TV]))
    calls = fake_incus.calls[vorher:]
    erstes_weg = next(i for i, c in enumerate(calls) if c[:4] == ["network", "acl", "rule", "remove"])
    assert any(c[:4] == ["network", "acl", "rule", "add"] and "action=reject" in c for c in calls[:erstes_weg])


def test_sperrliste_folgt_neuen_serveradressen(fake_incus, no_host, monkeypatch):
    run(network.ensure_network([TV]))
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "198.51.100.7/32"})
    assert run(network.sync_rules([TV])) is True
    dest = _reject_all(fake_incus)[0]["destination"]
    assert "198.51.100.7/32" in dest and "203.0.113.9/32" not in dest


def test_unlesbare_sperrliste(fake_incus, no_host):
    fake_incus.fail["network acl show"] = "boom"
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.sync_rules([TV]))
    assert e.value.code == "tvw_network_missing"


def test_reihenfolge_der_regeln_loest_keinen_neuen_abgleich_aus(fake_incus, no_host):
    """Fund beim Bau: Nach dem Nachziehen steht allow vorn. Ein Vergleich mit Reihenfolge meldete dann jedes Mal eine
    Änderung und baute die Regeln endlos um."""
    run(network.ensure_network([]))
    run(network.sync_rules([TV]))
    _egress(fake_incus).reverse()
    assert run(network.sync_rules([TV])) is False


def test_doppelte_regel_im_ist_wird_gemeldet_nicht_umgebaut(fake_incus, no_host):
    """incus entfernt bei zwei gleichen Regeln keine einzeln, --force nähme beide und damit kurz die Sperre weg."""
    run(network.ensure_network([TV]))
    _egress(fake_incus).append(dict(_reject_all(fake_incus)[0]))
    vorher = len(fake_incus.calls)
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.sync_rules([TV]))
    assert e.value.code == "tvw_acl_dirty"
    assert not [c for c in fake_incus.calls[vorher:] if "rule" in c]
