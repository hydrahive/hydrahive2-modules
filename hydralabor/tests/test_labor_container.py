"""Hydra-Labor L1 Schritt 2: Container anlegen, einrichten, Sicherungspunkt, Zurücksetzen (PLAN-L1.md).

Befund hydratest 30.10.: Das default-Profil kann security.privileged=true tragen → Labor ohne Profil, ausdrücklich
unprivilegiert. incus ist die Attrappe FakeIncus.
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
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "26.04")
    run(network.ensure_network())
    return fake_incus


def launch_args(fake):
    return next(c for c in fake.calls if c[0] == "launch")


# --- Grenzen ---------------------------------------------------------------------------------------------------

def test_standard_grenzen():
    lim = container.Limits()
    assert (lim.cpu, lim.ram_mb, lim.disk_gb) == (2, 4096, 20)


@pytest.mark.parametrize("kw", [{"cpu": 0}, {"cpu": 65}, {"ram_mb": 1023}, {"ram_mb": 262145},
                                {"disk_gb": 9}, {"disk_gb": 2001}, {"cpu": True}, {"cpu": "2"}])
def test_grenzen_ungueltig(kw):
    with pytest.raises(container.LaborError) as e:
        container.Limits(**kw)
    assert e.value.code == "labor_limits_invalid"


@pytest.mark.parametrize("kw", [{"cpu": 1}, {"cpu": 64}, {"ram_mb": 1024}, {"ram_mb": 262144},
                                {"disk_gb": 10}, {"disk_gb": 2000}])
def test_grenzen_raender_gueltig(kw):
    container.Limits(**kw)


# --- Anlegen ---------------------------------------------------------------------------------------------------

def test_launch_ohne_profil_unprivilegiert_eigenes_netz(net):
    run(container.launch(container.Limits(cpu=3, ram_mb=6144, disk_gb=30)))
    a = launch_args(net)
    assert a[-2:] == ["images:ubuntu/26.04", "hh-labor"] and a[-3] == "--"
    for opt in (["--no-profiles"], ["-s", "default"], ["-n", "hhlabor0"], ["-c", "limits.cpu=3"],
                ["-c", "limits.memory=6144MiB"], ["-c", "security.privileged=false"],
                ["-c", "security.nesting=true"], ["-d", "root,size=30GiB"]):
        assert any(a[i:i + len(opt)] == opt for i in range(len(a))), opt
    line = " ".join(a)
    assert "br0" not in line and "hhnat0" not in line and "privileged=true" not in line


def test_speicherpool_aus_standardprofil(net):
    net.pool = "ssd"
    run(container.launch(container.Limits()))
    a = launch_args(net)
    assert a[a.index("-s") + 1] == "ssd"


def test_kein_speicherpool_klare_meldung(net):
    net.pool = ""
    with pytest.raises(container.LaborError) as e:
        run(container.launch(container.Limits()))
    assert e.value.code == "labor_no_storage_pool"
    assert "hh-labor" not in net.containers


def test_launch_idempotent(net):
    run(container.launch(container.Limits()))
    run(container.launch(container.Limits()))
    assert sum(1 for c in net.calls if c[0] == "launch") == 1


def test_launch_fehler(net):
    net.fail["launch"] = "boom"
    with pytest.raises(container.LaborError) as e:
        run(container.launch(container.Limits()))
    assert e.value.code == "labor_launch_failed"


@pytest.mark.parametrize(("text", "ver"), [('VERSION_ID="26.04"\nID=ubuntu\n', "26.04"),
                                         ('VERSION_ID="24.04"\nID=ubuntu\n', "24.04"),
                                         ('VERSION_ID="12"\nID=debian\n', "24.04"), ("", "24.04"),
                                         ('VERSION_ID="26.04;rm"\nID=ubuntu\n', "24.04")])
def test_ubuntu_version_wie_server(text, ver, tmp_path):
    f = tmp_path / "os-release"
    f.write_text(text)
    assert container._ubuntu_version(f) == ver


def test_gateway_aus_netz(net):
    assert run(network.gateway()) == "10.77.0.1"


# --- Netzprobe nach dem Anlegen --------------------------------------------------------------------------------

def test_netz_offen_container_wird_entfernt(net):
    net.open_targets.add("10.77.0.1:443")
    with pytest.raises(network.LaborNetworkError) as e:
        run(container.launch_and_probe(container.Limits()))
    assert e.value.code == "labor_net_open"
    assert "hh-labor" not in net.containers
    assert ["delete", "hh-labor", "--force"] in net.calls


def test_netz_zu_container_bleibt(net):
    assert run(container.launch_and_probe(container.Limits())) == {"ok": True, "checked": 4}
    assert "hh-labor" in net.containers
