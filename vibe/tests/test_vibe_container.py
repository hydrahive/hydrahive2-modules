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
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "26.04")
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
    assert a[-2:] == ["images:ubuntu/26.04", "hh-vibe-p1"] and a[-3] == "--"
    for opt in (["--no-profiles"], ["-s", "default"], ["-n", "hhvibe0"], ["-c", "limits.cpu=3"],
                ["-c", "limits.memory=3072MiB"], ["-c", "security.privileged=false"],
                ["-c", "security.nesting=false"], ["-d", "root,size=12GiB"]):
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


@pytest.mark.parametrize(("text", "ver"), [('VERSION_ID="26.04"\nID=ubuntu\n', "26.04"),
                                         ('VERSION_ID="24.04"\nID=ubuntu\n', "24.04"),
                                         ('VERSION_ID="12"\nID=debian\n', "24.04"), ("", "24.04"),
                                         ('VERSION_ID="26.04;rm"\nID=ubuntu\n', "24.04"),
                                         ('VERSION_ID="22.04"\nID=pop\n', "24.04")])
def test_ubuntu_version_wie_server(text, ver, tmp_path):
    f = tmp_path / "os-release"
    f.write_text(text)
    assert container._ubuntu_version(f) == ver


def test_ubuntu_version_datei_fehlt(tmp_path):
    assert container._ubuntu_version(tmp_path / "gibt-es-nicht") == "24.04"


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
