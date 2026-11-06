"""Baustein 2: Container hh-vibe-<id> anlegen, ruhen, wecken, entfernen (PLAN-V1.md).

Wie beim Labor ohne Profil, ausdrücklich unprivilegiert, mit eigener Platte im Standard-Speicherpool und NIC am
Vibe-Netz. Anders als beim Labor gibt es mehrere Container; der Name kommt aus einer Projekt-ID und wird geprüft.
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


def launch_args(fake, name="hh-vibe-p1"):
    return next(c for c in fake.calls if c[0] == "launch" and c[-1] == name)


# --- Namen -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("pid", ["p1", "abc123", "019e-aa-bb", "a" * 40])
def test_name_aus_projekt_id(pid):
    n = container.name_for(pid)
    assert n == f"hh-vibe-{pid}" and len(n) <= 63


@pytest.mark.parametrize("pid", ["", "P1", "a b", "a;b", "a/b", "-x", "../x", "a" * 80, "ä", "p1\n"])
def test_name_komische_id_abgelehnt(pid):
    with pytest.raises(container.VibeError) as e:
        container.name_for(pid)
    assert e.value.code == "vibe_name_invalid"


def test_nur_eigene_container_gelten_als_vibe():
    assert container.is_vibe_name("hh-vibe-p1") is True
    for fremd in ("hh-labor", "hydratest", "hh-vibe", "hh-vibe-", "xhh-vibe-p1", "hh-vibe-P1"):
        assert container.is_vibe_name(fremd) is False


# --- Grenzen ---------------------------------------------------------------------------------------------------

def test_standard_grenzen_aus_dem_plan():
    lim = container.Limits()
    assert (lim.cpu, lim.ram_mb, lim.disk_gb) == (2, 2048, 10)


@pytest.mark.parametrize("kw", [{"cpu": 0}, {"cpu": 17}, {"ram_mb": 511}, {"ram_mb": 32769},
                                {"disk_gb": 1}, {"disk_gb": 201}, {"cpu": True}, {"cpu": "2"}])
def test_grenzen_ungueltig(kw):
    with pytest.raises(container.VibeError) as e:
        container.Limits(**kw)
    assert e.value.code == "vibe_limits_invalid"


@pytest.mark.parametrize("kw", [{"cpu": 1}, {"cpu": 16}, {"ram_mb": 512}, {"ram_mb": 32768},
                                {"disk_gb": 2}, {"disk_gb": 200}])
def test_grenzen_raender_gueltig(kw):
    container.Limits(**kw)


# --- Anlegen ---------------------------------------------------------------------------------------------------

def test_launch_ohne_profil_unprivilegiert_eigenes_netz(net):
    run(container.launch("p1", container.Limits(cpu=3, ram_mb=3072, disk_gb=12)))
    a = launch_args(net)
    assert a[-2:] == ["images:ubuntu/24.04", "hh-vibe-p1"] and a[-3] == "--"
    for opt in (["--no-profiles"], ["-s", "default"], ["-n", "hhvibe0"], ["-c", "limits.cpu=3"],
                ["-c", "limits.memory=3072MiB"], ["-c", "security.privileged=false"],
                ["-c", "security.nesting=false"], ["-c", "security.idmap.isolated=true"],
                ["-d", "root,size=12GiB"]):
        assert any(a[i:i + len(opt)] == opt for i in range(len(a))), opt
    line = " ".join(a)
    assert "br0" not in line and "hhnat0" not in line and "hhlabor0" not in line and "privileged=true" not in line


def test_kein_nesting_im_gegensatz_zum_labor(net):
    """Vibe baut Webseiten, keine Container. Verschachtelung öffnet nur mehr Angriffsfläche."""
    run(container.launch("p1", container.Limits()))
    assert ["-c", "security.nesting=true"] not in [launch_args(net)[i:i + 2] for i in range(len(launch_args(net)))]


def test_speicherpool_aus_standardprofil(net):
    net.pool = "ssd"
    run(container.launch("p1", container.Limits()))
    a = launch_args(net)
    assert a[a.index("-s") + 1] == "ssd"


@pytest.mark.parametrize("pool", ["bad pool", "-x", "a;b", "a/b", ""])
def test_kein_oder_komischer_speicherpool_klare_meldung(net, pool):
    net.pool = pool
    with pytest.raises(container.VibeError) as e:
        run(container.launch("p1", container.Limits()))
    assert e.value.code == "vibe_no_storage_pool"
    assert "hh-vibe-p1" not in net.containers


def test_launch_idempotent(net):
    run(container.launch("p1", container.Limits()))
    run(container.launch("p1", container.Limits()))
    assert sum(1 for c in net.calls if c[0] == "launch") == 1


def test_zwei_projekte_zwei_container_ein_netz(net):
    run(container.launch("p1", container.Limits()))
    run(container.launch("p2", container.Limits()))
    assert set(net.containers) == {"hh-vibe-p1", "hh-vibe-p2"}
    assert {c["network"] for c in net.containers.values()} == {"hhvibe0"}
    assert sum(1 for c in net.calls if c[:2] == ["network", "create"]) == 1


def test_launch_fehler(net):
    net.fail["launch"] = "boom"
    with pytest.raises(container.VibeError) as e:
        run(container.launch("p1", container.Limits()))
    assert e.value.code == "vibe_launch_failed"
