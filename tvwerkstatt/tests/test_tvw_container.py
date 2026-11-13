"""Baustein 3: der Bau-Container hh-tvwerkstatt (feste Grenzen, eigenes Netz, Anhalten, Abbauen)."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, network


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def schnell(monkeypatch):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})


def _launch(fake) -> list[str]:
    return next(c for c in fake.calls if c[0] == "launch")


def test_status_ohne_container(fake_incus):
    assert run(container.status()) == "missing"


def test_status_liste_unlesbar(fake_incus):
    fake_incus.fail["list --format json"] = "boom"
    assert run(container.status()) == "unknown"


def test_anlegen_mit_festen_grenzen(fake_incus):
    run(container.ensure_running())
    a = _launch(fake_incus)
    assert a[-2:] == ["images:ubuntu/24.04", "hh-tvwerkstatt"]
    assert "--no-profiles" in a and a[a.index("-n") + 1] == network.NET and a[a.index("-s") + 1] == "ssd"
    cfg = [a[i + 1] for i, x in enumerate(a) if x == "-c"]
    for need in ("security.privileged=false", "security.nesting=false", "security.idmap.isolated=true"):
        assert need in cfg
    assert run(container.status()) == "running"


def test_nie_an_hhnat0_oder_br0(fake_incus):
    run(container.ensure_running())
    a = _launch(fake_incus)
    assert "hhnat0" not in a and "br0" not in a


def test_bestehender_gestoppter_wird_gestartet_nicht_neu_angelegt(fake_incus):
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": network.NET}
    run(container.ensure_running())
    assert not [c for c in fake_incus.calls if c[0] == "launch"]
    assert ["start", "hh-tvwerkstatt"] in fake_incus.calls


def test_anlegen_scheitert(fake_incus):
    fake_incus.fail["launch"] = "boom"
    with pytest.raises(container.TvwContainerError) as e:
        run(container.ensure_running())
    assert e.value.code == "tvw_launch_failed"


@pytest.mark.parametrize("pool", ["", "a b", "../x"])
def test_kein_gueltiger_speicherpool(fake_incus, pool):
    fake_incus.pool = pool
    with pytest.raises(container.TvwContainerError) as e:
        run(container.ensure_running())
    assert e.value.code == "tvw_no_storage_pool"


def test_keine_adresse(fake_incus, monkeypatch):
    monkeypatch.setattr(container, "_WAIT_TRIES", 3)
    fake_incus.containers["hh-tvwerkstatt"] = {"running": True, "network": network.NET}
    fake_incus.exec_answers["ip -4 -o addr show eth0"] = (1, "")
    with pytest.raises(container.TvwContainerError) as e:
        run(container.wait_for_address())
    assert e.value.code == "tvw_no_address"


def test_anhalten(fake_incus):
    fake_incus.containers["hh-tvwerkstatt"] = {"running": True, "network": network.NET}
    run(container.stop())
    assert run(container.status()) == "stopped"


def test_anhalten_ohne_container_ist_kein_fehler(fake_incus):
    run(container.stop())
    assert not [c for c in fake_incus.calls if c[0] == "stop"]


def test_abbauen_nimmt_netz_mit_fremde_bleiben(fake_incus):
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": network.NET}
    fake_incus.containers["hh-labor"] = {"running": True, "network": "hhlabor0"}
    run(container.remove())
    assert "hh-tvwerkstatt" not in fake_incus.containers and "hh-labor" in fake_incus.containers
    assert network.NET not in fake_incus.networks and network.ACL not in fake_incus.acls


def test_loeschen_trifft_nur_den_eigenen_namen(fake_incus):
    fake_incus.containers["hh-tvwerkstatt"] = {"running": True, "network": network.NET}
    run(container.remove())
    assert [c for c in fake_incus.calls if c[0] == "delete"] == [["delete", "hh-tvwerkstatt", "--force"]]
