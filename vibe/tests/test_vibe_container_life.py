"""Baustein 2: Container nach dem Anlegen – Netzprobe, ruhen, wecken, entfernen (PLAN-V1.md).

Zweiter Teil zu test_vibe_container.py (Datei geteilt: höchstens 200 Zeilen je Datei).
"""
from __future__ import annotations

import asyncio

import pytest
from backend import container, network


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    run(network.ensure_network())
    return fake_incus


# --- Netzprobe nach dem Anlegen --------------------------------------------------------------------------------

def test_netz_offen_container_wird_entfernt(net):
    net.open_targets.add("10.79.0.1:443")
    with pytest.raises(network.VibeNetworkError) as e:
        run(container.launch_and_probe("p1", container.Limits()))
    assert e.value.code == "vibe_net_open"
    assert "hh-vibe-p1" not in net.containers
    assert ["delete", "hh-vibe-p1", "--force"] in net.calls


def test_netz_zu_container_bleibt(net):
    assert run(container.launch_and_probe("p1", container.Limits())) == {"ok": True, "checked": 4}
    assert "hh-vibe-p1" in net.containers


def test_wartet_auf_adresse_vor_probe(net, monkeypatch):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    tries = {"n": 0}
    orig = net.run

    async def flaky(*a, **k):
        if a[:1] == ("exec",) and "ip -4 -o addr show eth0" in a[-1]:
            tries["n"] += 1
            return (0, "2: eth0 inet 10.79.0.5/24\n", "") if tries["n"] >= 3 else (1, "", "")
        return await orig(*a, **k)
    monkeypatch.setattr(container.incus, "run", flaky)
    assert run(container.launch_and_probe("p1", container.Limits()))["ok"] is True
    assert tries["n"] == 3


def test_keine_adresse_klare_meldung_und_container_weg(net, monkeypatch):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    net.exec_answers["ip -4 -o addr show eth0"] = (1, "")
    with pytest.raises(container.VibeError) as e:
        run(container.launch_and_probe("p1", container.Limits()))
    assert e.value.code == "vibe_no_address"
    assert "hh-vibe-p1" not in net.containers
    assert sum(1 for c in net.calls if c[0] == "exec" and "ip -4 -o addr" in c[-1]) == container._WAIT_TRIES


# --- ruhen / wecken / entfernen --------------------------------------------------------------------------------

def test_ruhen_und_wecken(net):
    run(container.launch("p1", container.Limits()))
    assert run(container.running("p1")) is True
    run(container.stop("p1"))
    assert run(container.running("p1")) is False
    run(container.start("p1"))
    assert run(container.running("p1")) is True


def test_running_unterscheidet_projekte(net):
    run(container.launch("p1", container.Limits()))
    run(container.launch("p2", container.Limits()))
    run(container.stop("p2"))
    assert run(container.running("p1")) is True and run(container.running("p2")) is False


def test_remove_nur_der_eigene_container(net):
    run(container.launch("p1", container.Limits()))
    run(container.launch("p2", container.Limits()))
    net.containers["hh-labor"] = {"running": True, "network": "hhlabor0"}
    run(container.remove("p1"))
    assert set(net.containers) == {"hh-vibe-p2", "hh-labor"}


def test_remove_bei_komischer_id_fasst_nichts_an(net):
    net.containers["hh-labor"] = {"running": True, "network": "hhlabor0"}
    with pytest.raises(container.VibeError):
        run(container.remove("../hh-labor"))
    assert not any(c[0] == "delete" for c in net.calls)
    assert "hh-labor" in net.containers


def test_alle_vibe_container_nur_mit_praefix(net):
    run(container.launch("p1", container.Limits()))
    net.containers["hh-labor"] = {"running": True, "network": "hhlabor0"}
    net.containers["hydratest"] = {"running": True, "network": ""}
    assert run(container.all_names()) == {"hh-vibe-p1"}
