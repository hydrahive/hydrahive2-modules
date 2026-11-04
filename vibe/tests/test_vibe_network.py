"""Baustein 2: eigenes Netz hhvibe0 + Sperrliste hhvibe-acl (PLAN-V1.md Entscheidung 2).

incus ist die FakeIncus-Attrappe. Kein echter Container in der Unit-Suite. Das Netz teilen sich alle Vibe-Projekte.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import network


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def no_host(monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "203.0.113.9/32"})


def test_eigene_namen_nicht_die_des_labors():
    assert network.NET == "hhvibe0" and network.ACL == "hhvibe-acl"
    assert network.NET != "hhlabor0" and network.ACL != "hhlabor-acl"


def test_teilnetze_ueberschneiden_sich_nicht_mit_dem_labor():
    labor = {"10.77.0.0/24", "10.78.0.0/24", "172.31.77.0/24"}
    assert not labor & set(network._CANDIDATES)


def test_freies_subnetz_aus_vorrat(fake_incus, monkeypatch):
    first = network._CANDIDATES[0]
    monkeypatch.setattr(network, "_host_networks", lambda: {first, "192.168.178.0/24"})
    assert network.choose_subnet() == network._CANDIDATES[1]


def test_alle_subnetze_belegt_klare_meldung(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set(network._CANDIDATES))
    with pytest.raises(network.VibeNetworkError) as e:
        network.choose_subnet()
    assert e.value.code == "vibe_subnet_unavailable"


def test_acl_sperrt_private_tailscale_loopback_und_server(fake_incus, no_host):
    run(network.ensure_network())
    assert network.NET in fake_incus.networks and network.ACL in fake_incus.acls
    rules = fake_incus.acls[network.ACL]["egress"]
    reject = [r for r in rules if r.get("action") == "reject"]
    allow = [r for r in rules if r.get("action") == "allow"]
    assert len(reject) == 1 and len(allow) == 1
    dest = reject[0]["destination"]
    for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "127.0.0.0/8",
                "fc00::/7", "fe80::/10", "192.168.178.2/32", "203.0.113.9/32"):
        assert net in dest
    assert fake_incus.networks[network.NET]["security.acls"] == network.ACL


def test_sperrregel_ist_eingeschaltet(fake_incus, no_host):
    run(network.ensure_network())
    assert all(r["state"] == "enabled" for r in fake_incus.acls[network.ACL]["egress"])


def test_netz_idempotent(fake_incus, no_host):
    run(network.ensure_network())
    before = len(fake_incus.calls)
    run(network.ensure_network())
    assert all(c[-3:] == ["list", "--format", "csv"] for c in fake_incus.calls[before:])
    assert list(fake_incus.networks).count(network.NET) == 1


def test_acl_und_netz_in_richtiger_reihenfolge(fake_incus, no_host):
    run(network.ensure_network())
    actions = [" ".join(c) for c in fake_incus.calls]
    created = next(a for a in actions if a.startswith(f"network create {network.NET}"))
    assert actions.index(f"network acl create {network.ACL}") < actions.index(created)
    assert "ipv6.address=none" in created and "ipv4.nat=true" in created
    assert actions.index(created) < actions.index(f"network set {network.NET} security.acls={network.ACL}")


def test_netz_da_sperre_fehlt_sperre_wird_nachgezogen(fake_incus, no_host):
    fake_incus.networks[network.NET] = {"ipv4.address": "10.79.0.1/24"}
    run(network.ensure_network())
    assert network.ACL in fake_incus.acls
    assert fake_incus.networks[network.NET]["security.acls"] == network.ACL
    assert not any(c[:2] == ["network", "create"] for c in fake_incus.calls)


@pytest.mark.parametrize("stelle", ["network acl create", "network acl rule add", "network create", "network set"])
def test_incus_fehler_bricht_ab(fake_incus, no_host, stelle):
    fake_incus.fail[stelle] = "boom"
    with pytest.raises(network.VibeNetworkError) as e:
        run(network.ensure_network())
    assert e.value.code == "vibe_incus_failed"


def test_sperrliste_folgt_neuen_serveradressen(fake_incus, no_host, monkeypatch):
    run(network.ensure_network())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "198.51.100.7/32"})
    assert run(network.sync_rules()) is True
    dest = [r for r in fake_incus.acls[network.ACL]["egress"] if r["action"] == "reject"]
    assert len(dest) == 1 and "198.51.100.7/32" in dest[0]["destination"]
    assert "203.0.113.9/32" not in dest[0]["destination"]
    assert run(network.sync_rules()) is False


# --- Probe -----------------------------------------------------------------------------------------------------

def test_probe_ziele_gateway_und_alle_serveradressen(no_host):
    t = network.probe_targets("10.79.0.1")
    for h in ("10.79.0.1", "192.168.178.2", "203.0.113.9"):
        assert f"{h}:443" in t and f"{h}:22" in t


def test_probe_ziele_enthalten_nie_router_und_fritzbox_von_till(no_host):
    """Regel von Till: 192.168.178.1 und .3 werden nie angesprochen, auch nicht bei einer Sperrprobe."""
    t = " ".join(network.probe_targets("10.79.0.1"))
    assert "192.168.178.1:" not in t and "192.168.178.3:" not in t


@pytest.mark.parametrize("offen", ["10.79.0.1:443", "203.0.113.9:22", "192.168.178.2:443"])
def test_probe_ein_ziel_offen_bricht_ab(fake_incus, no_host, offen):
    fake_incus.open_targets.add(offen)
    with pytest.raises(network.VibeNetworkError) as e:
        run(network.probe("hh-vibe-p1", "10.79.0.1"))
    assert e.value.code == "vibe_net_open"


def test_probe_gruen(fake_incus, no_host):
    assert run(network.probe("hh-vibe-p1", "10.79.0.1")) == {"ok": True, "checked": 6}
    assert fake_incus.calls[-1][:3] == ["exec", "hh-vibe-p1", "--"]


def test_probe_dns_fehler(fake_incus, no_host):
    fake_incus.dns_ok = False
    with pytest.raises(network.VibeNetworkError) as e:
        run(network.probe("hh-vibe-p1", "10.79.0.1"))
    assert e.value.code == "vibe_dns_failed"


def test_probe_exec_fehler(fake_incus, no_host):
    fake_incus.fail["exec hh-vibe-p1"] = "boom"
    with pytest.raises(network.VibeNetworkError) as e:
        run(network.probe("hh-vibe-p1", "10.79.0.1"))
    assert e.value.code == "vibe_net_probe_failed"


def test_gateway_aus_netz(fake_incus, no_host):
    run(network.ensure_network())
    assert run(network.gateway()) == network.gateway_of(network._CANDIDATES[0])


def test_gateway_fehlt(fake_incus):
    fake_incus.fail["network get"] = "not found"
    with pytest.raises(network.VibeNetworkError) as e:
        run(network.gateway())
    assert e.value.code == "vibe_network_missing"


# --- Aufräumen: ein Netz für mehrere Projekte ------------------------------------------------------------------

def test_netz_bleibt_solange_container_daran_haengen(fake_incus, no_host):
    run(network.ensure_network())
    fake_incus.containers["hh-vibe-p1"] = {"running": True, "network": network.NET}
    assert run(network.remove_if_unused()) is False
    assert network.NET in fake_incus.networks and network.ACL in fake_incus.acls


def test_netz_weg_wenn_kein_container_mehr_daran_haengt(fake_incus, no_host):
    run(network.ensure_network())
    assert run(network.remove_if_unused()) is True
    assert network.NET not in fake_incus.networks and network.ACL not in fake_incus.acls


def test_aufraeumen_fasst_das_labor_netz_nie_an(fake_incus, no_host):
    fake_incus.networks["hhlabor0"] = {"ipv4.address": "10.77.0.1/24"}
    fake_incus.acls["hhlabor-acl"] = {"egress": [], "ingress": []}
    run(network.ensure_network())
    run(network.remove_if_unused())
    assert "hhlabor0" in fake_incus.networks and "hhlabor-acl" in fake_incus.acls
    assert not any(c[:3] in (["network", "delete", "hhlabor0"], ["network", "acl", "delete"]) and "hhlabor" in " ".join(c)
                   for c in fake_incus.calls)


def test_aufraeumen_bei_unlesbarer_containerliste_loescht_nichts(fake_incus, no_host):
    """Kann die Containerliste nicht gelesen werden, gilt das Netz als benutzt (fail-closed)."""
    run(network.ensure_network())
    fake_incus.fail["list"] = "boom"
    assert run(network.remove_if_unused()) is False
    assert network.NET in fake_incus.networks


def test_container_an_fremdem_netz_halten_das_vibe_netz_nicht_fest(fake_incus, no_host):
    """Mutanten-Fund: Ein Container am Netz des Labors (oder am Standardnetz) darf das Aufräumen nicht verhindern."""
    run(network.ensure_network())
    fake_incus.containers["hh-labor"] = {"running": True, "network": "hhlabor0"}
    fake_incus.containers["hydratest"] = {"running": True, "network": "hhnat0"}
    assert run(network.remove_if_unused()) is True
    assert network.NET not in fake_incus.networks
