"""Hydra-Labor L1 Schritt 2: Einrichtung im Container, Sicherungspunkt „frisch“, Zurücksetzen, Entfernen."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, network, provision


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def lab(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "24.04")
    run(network.ensure_network())
    run(container.launch(container.Limits()))
    return fake_incus


def execs(fake):
    return [c for c in fake.calls if c[0] == "exec"]


def test_einrichtung_alle_schritte_in_reihenfolge(lab):
    seen = []
    run(provision.setup(seen.append))
    assert seen == [s.key for s in provision.STEPS]
    assert [s.key for s in provision.STEPS] == ["user", "packages", "node", "code", "python", "frontend", "links"]
    assert len(execs(lab)) == len(provision.STEPS)


def test_nutzerschritte_als_labor_rootschritte_als_root(lab):
    run(provision.setup(lambda _k: None))
    for step, call in zip(provision.STEPS, execs(lab), strict=True):
        as_user = call[call.index("--user") + 1] if "--user" in call else None
        assert as_user == ("1000" if step.as_user else None), step.key
        if step.as_user:
            assert call[call.index("--cwd") + 1] == "/work"
            assert "HOME=/home/labor" in call


def test_genau_diese_schritte_als_labor():
    assert [s.key for s in provision.STEPS if s.as_user] == ["code", "python", "frontend"]


def test_pakete_fuer_kern_tests():
    script = next(s.script for s in provision.STEPS if s.key == "packages")
    for pkg in ("git", "python3-venv", "build-essential", "ripgrep", "qemu-utils", "lsof"):
        assert f" {pkg}" in script


def test_klon_ohne_zugangsdaten(lab):
    script = next(s.script for s in provision.STEPS if s.key == "code")
    assert "https://github.com/hydrahive/hydrahive2.0.git" in script
    assert "https://github.com/hydrahive/hydrahive2-modules.git" in script
    assert "@github.com" not in script and "TOKEN" not in script.upper()


def test_labor_nutzer_ohne_sudo(lab):
    script = next(s.script for s in provision.STEPS if s.key == "user")
    assert "gpasswd -d labor sudo" in script and "/etc/sudoers.d/" in script


def test_venv_als_standard_python(lab):
    script = next(s.script for s in provision.STEPS if s.key == "links")
    for tool in ("pip", "pytest", "ruff"):
        assert f"ln -sf /work/.venv/bin/{tool} /usr/local/bin/{tool}" in script
    for tool in ("python", "python3"):          # Startskript, keine Verknüpfung (venv sonst nicht erkannt)
        assert f"exec /work/.venv/bin/{tool} " in script
        assert f"> /usr/local/bin/{tool}; chmod 755 /usr/local/bin/{tool}" in script
        assert f"ln -sf /work/.venv/bin/{tool} " not in script


def test_schritt_scheitert_meldet_schritt(lab):
    lab.exec_answers["nodesource"] = (1, "")
    seen = []
    with pytest.raises(provision.SetupError) as e:
        run(provision.setup(seen.append))
    assert e.value.code == "labor_setup_failed" and e.value.step == "node"
    assert seen == ["user", "packages", "node"]


def test_sicherungspunkt_gestoppt_angelegt(lab):
    run(provision.snapshot())
    acts = [c[:3] for c in lab.calls if c[0] in ("stop", "start") or c[:2] == ["snapshot", "create"]]
    assert acts == [["stop", "hh-labor"], ["snapshot", "create", "hh-labor"], ["start", "hh-labor"]]
    assert lab.snapshots["hh-labor"] == {"frisch"}
    assert run(provision.has_snapshot()) is True


def test_sicherungspunkt_schon_da_nichts_doppelt(lab):
    run(provision.snapshot())
    n = len(lab.calls)
    run(provision.snapshot())
    assert not any(c[:2] == ["snapshot", "create"] for c in lab.calls[n:])


def test_zuruecksetzen_nur_frisch_nur_hh_labor_dann_netzprobe(lab):
    run(provision.snapshot())
    res = run(provision.reset())
    restore = next(c for c in lab.calls if c[:2] == ["snapshot", "restore"])
    assert restore == ["snapshot", "restore", "hh-labor", "frisch"]
    after = lab.calls[lab.calls.index(restore) + 1:]
    assert ["start", "hh-labor"] in after
    assert any(c[0] == "exec" and "hh-labor-netprobe" in c[-1] for c in after)
    assert res["ok"] is True


def test_zuruecksetzen_ohne_sicherungspunkt(lab):
    with pytest.raises(container.LaborError) as e:
        run(provision.reset())
    assert e.value.code == "labor_no_snapshot"


def test_zuruecksetzen_restore_fehler(lab):
    run(provision.snapshot())
    lab.fail["snapshot restore"] = "boom"
    with pytest.raises(container.LaborError) as e:
        run(provision.reset())
    assert e.value.code == "labor_reset_failed"


def test_entfernen_nur_hh_labor(lab):
    run(container.remove())
    assert [c for c in lab.calls if c[0] == "delete"] == [["delete", "hh-labor", "--force"]]
    assert "hh-labor" not in lab.containers


def test_netz_entfernen_nur_eigenes(lab):
    run(network.remove())
    dels = [c for c in lab.calls if c[1:2] in (["delete"],) or c[:3] == ["network", "acl", "delete"]]
    assert dels == [["network", "delete", "hhlabor0"], ["network", "acl", "delete", "hhlabor-acl"]]


def test_zuruecksetzen_wartet_auf_adresse_vor_probe(lab):
    run(provision.snapshot())
    run(provision.reset())
    after = lab.calls[next(i for i, c in enumerate(lab.calls) if c[:2] == ["snapshot", "restore"]):]
    wait = next(i for i, c in enumerate(after) if c[0] == "exec" and "ip -4 -o addr" in c[-1])
    probe = next(i for i, c in enumerate(after) if c[0] == "exec" and "hh-labor-netprobe" in c[-1])
    assert wait < probe
