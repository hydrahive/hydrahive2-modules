"""H3 aus dem Review vom 6.11.: Rechte des gemeinsamen Workspaces vollständig statt additiv setzen (zweiter Teil zu
test_vibe_workspace_hardening.py)."""

from __future__ import annotations

import asyncio
import os
import shutil
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


def test_h3_baum_wird_vollstaendig_neu_gesetzt(tmp_path) -> None:
    if not _acl_works(tmp_path):
        pytest.skip("Dateisystem ohne POSIX-ACL")
    (tmp_path / ".probe").unlink()
    tree = tmp_path / "ws"
    (tree / "src").mkdir(parents=True)
    f = tree / "src" / "a.txt"
    f.write_text("a", encoding="utf-8")
    os.chmod(f, 0o666)  # o+w
    subprocess.run(["setfacl", "-m", "u:4242:rwx", str(f)], check=True)  # alter Principal
    subprocess.run(["setfacl", "-d", "-m", "u:4242:rwx", str(tree)], check=True)

    workspace_acl._apply_tree(tree, 1066536, 1066536)

    listing = subprocess.run(["getfacl", "-p", "-c", str(f)], check=False, capture_output=True, text=True).stdout
    assert "user:4242" not in listing and "user:1066536:rw" in listing
    assert "other::r--" in listing and "other::rw" not in listing
    root = subprocess.run(["getfacl", "-p", "-c", str(tree)], check=False, capture_output=True, text=True).stdout
    assert "default:user:4242" not in root and "default:other::r-x" in root


def test_h3_wurzel_sperrt_fremde_nutzer_aus_und_raeumt_alte_eintraege(tmp_path) -> None:
    if not _acl_works(tmp_path):
        pytest.skip("Dateisystem ohne POSIX-ACL")
    (tmp_path / ".probe").unlink()
    root = tmp_path / "ws"
    root.mkdir()
    os.chmod(root, 0o2775)
    subprocess.run(["setfacl", "-m", "u:4242:rwx", str(root)], check=True)
    subprocess.run(["setfacl", "-d", "-m", "u:4343:rwx", str(root)], check=True)   # alter Default-Principal

    workspace_acl._apply(root, 1066536, 1066536)

    listing = subprocess.run(["getfacl", "-p", "-c", str(root)], check=False, capture_output=True, text=True).stdout
    assert "user:4242" not in listing
    assert "user:4343" not in listing, "Review 2: `setfacl -b` lässt Default-ACLs stehen, `-k` ist nötig"
    assert "other::r-x" in listing and "default:other::r-x" in listing
    assert "user:1066536:rwx" in listing
