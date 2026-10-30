"""Hydra-Labor L3 Baustein 4: eingehende Regel – nur vom Server-Gateway, nur TCP 8001; ausgehend unverändert."""
from __future__ import annotations

import asyncio

import pytest
from backend import network, probe_net


def run(c):
    return asyncio.run(c)


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    run(network.ensure_network())
    return fake_incus


def ingress(fake):
    return fake.acls["hhlabor-acl"]["ingress"]


def test_port_fest():
    assert probe_net.PORT == 8001


def test_freigeben_genau_eine_regel(net):
    egress_vorher = [dict(r) for r in net.acls["hhlabor-acl"]["egress"]]
    run(probe_net.open_port())
    assert ingress(net) == [{"action": "allow", "source": "10.77.0.1/32", "protocol": "tcp",
                             "destination_port": "8001", "state": "enabled"}]
    assert net.acls["hhlabor-acl"]["egress"] == egress_vorher


def test_freigeben_zweimal_keine_doppelte_regel(net):
    run(probe_net.open_port())
    run(probe_net.open_port())
    assert len(ingress(net)) == 1


def test_schliessen(net):
    run(probe_net.open_port())
    run(probe_net.close_port())
    assert ingress(net) == []


def test_schliessen_ohne_regel_kein_fehler(net):
    run(probe_net.close_port())
    assert ingress(net) == []


def test_fremde_eingehende_regel_bleibt(net):
    net.acls["hhlabor-acl"]["ingress"].append({"action": "allow", "source": "1.2.3.4/32", "state": "enabled"})
    run(probe_net.open_port())
    run(probe_net.close_port())
    assert ingress(net) == [{"action": "allow", "source": "1.2.3.4/32", "state": "enabled"}]


def test_offen(net):
    assert run(probe_net.is_open()) is False
    run(probe_net.open_port())
    assert run(probe_net.is_open()) is True


def test_fehler_von_incus(net):
    net.fail["network acl rule add"] = "boom"
    with pytest.raises(network.LaborNetworkError) as e:
        run(probe_net.open_port())
    assert e.value.code == "labor_incus_failed"


def test_netzprobe_unveraendert_mit_offenem_port(net):
    """Die Sperre nach außen (Labor → Server) bleibt; die Probe aus L1 prüft weiter dieselben Ziele."""
    run(probe_net.open_port())
    assert run(network.probe("hh-labor", "10.77.0.1"))["ok"] is True
