"""H3 aus dem Review vom 6.11.: `o+w` im Normalbetrieb entfernen (Host per Dateideskriptor, Container als UID 1000) –
zweiter Teil zu test_vibe_workspace_rights.py."""

from __future__ import annotations

import asyncio
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import container, network, workspace, workspace_acl


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clean_workspace():
    for _ in range(2):
        path = ensure_workspace("p1")
        if path.exists():
            remove_test_tree(path)
        workspace.forget("p1")
    yield
    path = ensure_workspace("p1")
    if path.exists():
        remove_test_tree(path)
    workspace.forget("p1")


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    run(network.ensure_network())
    return fake_incus


def _with_data(fake) -> None:
    fake.exec_answers["find /work"] = (0, "/work/src/App.tsx\n")


def _device(fake) -> dict | None:
    return fake.containers[container.name_for("p1")]["devices"].get(workspace.DEVICE)


# --- H3: Rechte vollständig statt additiv ------------------------------------------------------------------------------


def _acl_works(path: Path) -> bool:
    if not shutil.which("setfacl") or not shutil.which("getfacl"):
        return False
    probe = path / ".probe"
    probe.write_text("x", encoding="utf-8")
    try:
        subprocess.run(["setfacl", "-m", "u:4242:r", str(probe)], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def test_h3_normalbetrieb_setzt_die_wurzel_erneut(net, monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(workspace_acl, "_run", lambda args: calls.append(args))
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))
    calls.clear()

    assert run(workspace.ensure("p1")) == "ready"

    joined = " ".join(" ".join(c) for c in calls)
    assert "-b" in joined and "o::r-x" in joined


def test_h3_normalbetrieb_nimmt_world_write_im_baum_zurueck(net) -> None:
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))
    host = ensure_workspace("p1")
    f = host / "App.tsx"
    f.write_text("x", encoding="utf-8")
    os.chmod(f, 0o666)

    assert run(workspace.ensure("p1")) == "ready"

    assert f.stat().st_mode & 0o002 == 0
    assert f.stat().st_mode & 0o060 == 0o060  # Gruppe behält Schreibrecht


def test_h3_symlink_wird_beim_aufraeumen_nicht_verfolgt(tmp_path) -> None:
    outside = tmp_path / "aussen.txt"
    outside.write_text("x", encoding="utf-8")
    os.chmod(outside, 0o666)
    tree = tmp_path / "ws"
    tree.mkdir()
    (tree / "link").symlink_to(outside)

    workspace_acl.strip_world_write(tree)

    assert outside.stat().st_mode & 0o002  # Ziel außerhalb bleibt unberührt


def test_h3_world_write_wird_im_laufenden_container_entfernt(net) -> None:
    """Echter Befund: Der Hostdienst darf Dateien der abgebildeten Container-UID nicht per `chmod` ändern (nicht
    Besitzer). Darum läuft das Entfernen von `o+w` zusätzlich IM Container als UID 1000."""
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))
    net.calls.clear()

    assert run(workspace.ensure("p1")) == "ready"

    execs = [c for c in net.calls if c[:1] == ["exec"] and "o-w" in " ".join(c)]
    assert len(execs) == 1
    call = execs[0]
    assert call[call.index("--user") + 1] == "1000"
    assert "-type" in call and "-perm" in call  # nie Symlinks anfassen: `! -type l`


def test_h3_gestoppter_container_wird_dafuer_nicht_gestartet(net) -> None:
    run(container.launch("p1", container.Limits()))
    run(workspace.attach_new("p1"))
    run(container.stop("p1"))
    net.calls.clear()

    assert run(workspace.ensure("p1")) == "ready"

    assert not [c for c in net.calls if c[:1] in (["exec"], ["start"])]


def test_h3_hostseitiges_chmod_folgt_nie_einem_symlink(tmp_path, monkeypatch) -> None:
    """Review 2 (TOCTOU): Zwischen Prüfung und `chmod` ersetzt der Container die Datei durch einen Symlink nach außen."""
    outside = tmp_path / "aussen.txt"
    outside.write_text("x", encoding="utf-8")
    os.chmod(outside, 0o640)
    tree = tmp_path / "ws"
    tree.mkdir()
    victim = tree / "x"
    victim.write_text("x", encoding="utf-8")
    os.chmod(victim, 0o666)
    real_chmod, real_fchmod = os.chmod, os.fchmod

    def swap() -> None:
        victim.unlink(missing_ok=True)
        victim.symlink_to(outside)                           # Wettlauf gewonnen

    def racing_chmod(path, mode, *a, **k):
        swap()
        return real_chmod(path, mode, *a, **k)

    def racing_fchmod(fd, mode):
        swap()
        return real_fchmod(fd, mode)

    monkeypatch.setattr(workspace_acl.os, "chmod", racing_chmod)
    monkeypatch.setattr(workspace_acl.os, "fchmod", racing_fchmod)

    workspace_acl.strip_world_write(tree)

    assert stat.S_IMODE(outside.stat().st_mode) == 0o640     # Ziel außerhalb unberührt


def test_h3_hostseitiges_aufraeumen_nimmt_world_write_zurueck(tmp_path) -> None:
    tree = tmp_path / "ws"
    (tree / "sub").mkdir(parents=True)
    f = tree / "sub" / "a.txt"
    f.write_text("x", encoding="utf-8")
    os.chmod(f, 0o666)
    os.chmod(tree / "sub", 0o777)

    workspace_acl.strip_world_write(tree)

    assert f.stat().st_mode & 0o002 == 0 and (tree / "sub").stat().st_mode & 0o002 == 0
    assert stat.S_IMODE(f.stat().st_mode) == 0o664


def test_h3_default_acl_wird_ausdruecklich_mit_k_entfernt(tmp_path, monkeypatch) -> None:
    """`setfacl -b` entfernt Default-ACLs nur in manchen Versionen (2.3.2 ja, laut Handbuch nicht zugesagt). Darum
    verlangt der Code `-k` ausdrücklich, unabhängig vom Ergebnis auf diesem Rechner."""
    calls: list[list[str]] = []
    monkeypatch.setattr(workspace_acl, "_run", lambda args: calls.append(args))
    root = tmp_path / "ws"
    root.mkdir()

    workspace_acl._apply(root, 1066536, 1066536)
    workspace_acl._apply_tree(root, 1066536, 1066536)

    assert any("-k" in c and "-m" not in c and "-d" not in c and "-R" not in c for c in calls)   # Wurzel
    assert any("-R" in c and "-k" in c for c in calls)                                           # Baum
    for index, call in enumerate(calls):
        if "-m" in call and "-d" not in call:
            before = [c for c in calls[:index] if "-b" in c]
            assert before, "Sollzustand darf erst nach dem Zurücksetzen gesetzt werden"
