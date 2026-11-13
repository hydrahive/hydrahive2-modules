"""Baustein 2, Teil 2: Netzprobe im Container und Aufräumen von Netz und Sperrliste.

incus ist die FakeIncus-Attrappe. Kein echter Container in der Unit-Suite. Die echte Messung steht in PLAN-E1.md.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import network

TV = ("192.168.178.200", 5555)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def no_host(monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32", "203.0.113.9/32"})


# --- Probe im Container ---------------------------------------------------------------------------------------

def test_probe_ziele(no_host):
    t = network.probe_targets("10.81.0.1", [TV])
    for h in ("10.81.0.1", "192.168.178.2", "203.0.113.9"):
        assert f"{h}:22" in t["closed"] and f"{h}:443" in t["closed"]
    assert "192.168.178.200:80" in t["closed"] and t["tv"] == ["192.168.178.200:5555"]
    alle = " ".join(t["closed"] + t["tv"])
    assert "192.168.178.1:" not in alle and "192.168.178.3:" not in alle    # Router und Fritzbox nie ansprechen


def test_probe_gruen(fake_incus, no_host):
    fake_incus.open_targets.add("192.168.178.200:5555")
    out = run(network.probe("hh-tvwerkstatt", "10.81.0.1", [TV]))
    assert out == {"ok": True, "checked": 7, "tv": {"192.168.178.200:5555": "offen"}}


def test_probe_fernseher_aus_ist_kein_fehler(fake_incus, no_host):
    out = run(network.probe("hh-tvwerkstatt", "10.81.0.1", [TV]))
    assert out["ok"] is True and out["tv"] == {"192.168.178.200:5555": "zu"}


@pytest.mark.parametrize("offen", ["10.81.0.1:443", "203.0.113.9:22", "192.168.178.200:80"])
def test_probe_gesperrtes_ziel_offen(fake_incus, no_host, offen):
    fake_incus.open_targets.add(offen)
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.probe("hh-tvwerkstatt", "10.81.0.1", [TV]))
    assert e.value.code == "tvw_net_open"


def test_probe_dns_fehler(fake_incus, no_host):
    fake_incus.dns_ok = False
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.probe("hh-tvwerkstatt", "10.81.0.1", [TV]))
    assert e.value.code == "tvw_dns_failed"


def test_probe_unvollstaendige_antwort_gilt_als_fehler(fake_incus, no_host):
    fake_incus.exec_answers["hh-tvw-netprobe"] = (0, "dns ok\n")
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.probe("hh-tvwerkstatt", "10.81.0.1", [TV]))
    assert e.value.code == "tvw_net_probe_failed"


def test_probe_exec_fehler(fake_incus, no_host):
    fake_incus.fail["exec hh-tvwerkstatt"] = "boom"
    with pytest.raises(network.TvwNetworkError) as e:
        run(network.probe("hh-tvwerkstatt", "10.81.0.1", [TV]))
    assert e.value.code == "tvw_net_probe_failed"


# --- Aufräumen ------------------------------------------------------------------------------------------------

def test_netz_bleibt_solange_ein_container_daran_haengt(fake_incus, no_host):
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": network.NET}
    assert run(network.remove_if_unused()) is False
    assert network.NET in fake_incus.networks


def test_netz_weg_wenn_unbenutzt_fremde_netze_bleiben(fake_incus, no_host):
    fake_incus.networks["hhvibe0"] = {}
    fake_incus.acls["hhvibe-acl"] = {"egress": [], "ingress": []}
    fake_incus.containers["hydratest"] = {"running": True, "network": "hhnat0"}
    run(network.ensure_network([]))
    assert run(network.remove_if_unused()) is True
    assert network.NET not in fake_incus.networks and network.ACL not in fake_incus.acls
    assert "hhvibe0" in fake_incus.networks and "hhvibe-acl" in fake_incus.acls and "hhnat0" in fake_incus.networks


def test_aufraeumen_bei_unlesbarer_containerliste_loescht_nichts(fake_incus, no_host):
    run(network.ensure_network([]))
    fake_incus.fail["list --format json"] = "boom"
    assert run(network.remove_if_unused()) is False
    assert network.NET in fake_incus.networks
