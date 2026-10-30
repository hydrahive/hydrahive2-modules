"""Hydra-Labor L1: eigenes Netz + ACL vor dem Container (PLAN-L1.md).

incus ist die FakeIncus-Attrappe. Kein echter Container in der Unit-Suite.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import network


@pytest.fixture
def state():
    return network.NetworkState(name="hhlabor0", acl="hhlabor-acl", subnet="10.77.0.0/24")


def run(coro):
    return asyncio.run(coro)


def test_freies_subnetz_aus_vorrat(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: {"10.77.0.0/24", "192.168.178.0/24"})
    assert network.choose_subnet() == "10.78.0.0/24"


def test_alle_subnetze_belegt_klare_meldung(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: {"10.77.0.0/24", "10.78.0.0/24", "172.31.77.0/24"})
    with pytest.raises(network.LaborNetworkError) as e:
        network.choose_subnet()
    assert e.value.code == "labor_subnet_unavailable"


def test_acl_regeln_sperren_private_tailscale_loopback_und_server(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: {"192.168.178.0/24"})
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "203.0.113.9/32"})
    run(network.ensure_network())
    assert "hhlabor0" in fake_incus.networks and "hhlabor-acl" in fake_incus.acls
    rules = fake_incus.acls["hhlabor-acl"]["egress"]
    reject = [r for r in rules if r.get("action") == "reject"]
    allow = [r for r in rules if r.get("action") == "allow"]
    assert len(reject) == 1 and len(allow) == 1
    dest = reject[0]["destination"]
    for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "127.0.0.0/8",
                "fc00::/7", "fe80::/10", "192.168.178.2/32", "203.0.113.9/32"):
        assert net in dest
    assert fake_incus.networks["hhlabor0"]["security.acls"] == "hhlabor-acl"


def test_netz_idempotent(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    run(network.ensure_network())
    before = len(fake_incus.calls)
    run(network.ensure_network())
    assert all(c[-4:] == ["--format", "csv", "-c", "n"] for c in fake_incus.calls[before:])
    assert list(fake_incus.networks).count("hhlabor0") == 1


@pytest.fixture
def no_host(monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "203.0.113.9/32"})


def test_probe_ziele_gateway_und_alle_serveradressen(no_host):
    t = network.probe_targets("10.77.0.1")
    for h in ("10.77.0.1", "192.168.178.2", "203.0.113.9"):
        assert f"{h}:443" in t and f"{h}:22" in t


@pytest.mark.parametrize("offen", ["10.77.0.1:443", "203.0.113.9:22", "192.168.178.2:443"])
def test_probe_ein_ziel_offen_bricht_ab(fake_incus, no_host, offen):
    fake_incus.open_targets.add(offen)
    with pytest.raises(network.LaborNetworkError) as e:
        run(network.probe("hh-labor", "10.77.0.1"))
    assert e.value.code == "labor_net_open"


def test_probe_gruen(fake_incus, no_host):
    assert run(network.probe("hh-labor", "10.77.0.1")) == {"ok": True, "checked": 6}
    assert fake_incus.calls[-1][:3] == ["exec", "hh-labor", "--"]


def test_probe_dns_fehler(fake_incus, no_host):
    fake_incus.dns_ok = False
    with pytest.raises(network.LaborNetworkError) as e:
        run(network.probe("hh-labor", "10.77.0.1"))
    assert e.value.code == "labor_dns_failed"


def test_probe_exec_fehler(fake_incus, no_host):
    fake_incus.fail["exec hh-labor"] = "boom"
    with pytest.raises(network.LaborNetworkError) as e:
        run(network.probe("hh-labor", "10.77.0.1"))
    assert e.value.code == "labor_net_probe_failed"


def test_acl_und_netz_in_richtiger_reihenfolge(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    run(network.ensure_network())
    actions = [" ".join(c) for c in fake_incus.calls]
    created = next(a for a in actions if a.startswith("network create hhlabor0"))
    assert actions.index("network acl create hhlabor-acl") < actions.index(created)
    assert "ipv4.address=10.77.0.1/24" in created and "ipv6.address=none" in created
    assert actions.index(created) < actions.index("network set hhlabor0 security.acls=hhlabor-acl")


def test_netz_da_sperre_fehlt_sperre_wird_nachgezogen(fake_incus, no_host):
    fake_incus.networks["hhlabor0"] = {"ipv4.address": "10.77.0.1/24"}
    run(network.ensure_network())
    assert "hhlabor-acl" in fake_incus.acls
    assert fake_incus.networks["hhlabor0"]["security.acls"] == "hhlabor-acl"
    assert not any(c[:2] == ["network", "create"] for c in fake_incus.calls)


def test_sperrregel_ist_eingeschaltet(fake_incus, no_host):
    run(network.ensure_network())
    assert all(r["state"] == "enabled" for r in fake_incus.acls["hhlabor-acl"]["egress"])


@pytest.mark.parametrize("stelle", ["network acl create", "network acl rule add", "network create", "network set"])
def test_incus_fehler_bricht_ab(fake_incus, no_host, stelle):
    fake_incus.fail[stelle] = "boom"
    with pytest.raises(network.LaborNetworkError) as e:
        run(network.ensure_network())
    assert e.value.code == "labor_incus_failed"
