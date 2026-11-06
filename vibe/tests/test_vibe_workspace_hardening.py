"""Härtung der Workspace-Migration nach dem unabhängigen Review vom 6.11. (H1–H3, M1, M2).

H1 Herkunftsnachweis des veröffentlichten Baums · H2 ein Vorgang je Projekt · H3 Rechte vollständig statt additiv ·
M1 Agentenläufe ruhigstellen statt nur nachsehen · M2 Pull gegen einen zweiten Pull prüfen.
"""

from __future__ import annotations

import asyncio
import json
import os

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


# --- H1: Herkunftsnachweis ------------------------------------------------------------------------------------------


def test_h1_marker_ohne_nachweis_veroeffentlicht_keinen_fremden_hostbestand(net) -> None:
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    host = ensure_workspace("p1")
    (host / "fremd.txt").write_text("nicht aus dem Pull", encoding="utf-8")
    workspace._marker("p1").write_text(
        json.dumps({"stage": "pulled", "was_running": True}), encoding="utf-8"
    )

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_migration_failed"
    assert _device(net) is None
    assert workspace._marker("p1").exists()  # nichts wird „aufgeräumt“, bis ein Mensch es prüft
    assert (host / "fremd.txt").exists()


def test_h1_marker_mit_falscher_inode_wird_abgelehnt(net) -> None:
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    host = ensure_workspace("p1")
    (host / "x.txt").write_text("x", encoding="utf-8")
    state = {"stage": "pulled", "was_running": False, "source_dev": host.stat().st_dev, "source_ino": 1}
    workspace._marker("p1").write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_migration_failed"


def test_h1_echter_ablauf_speichert_die_inode_des_gezogenen_baums(net) -> None:
    run(container.launch("p1", container.Limits()))
    _with_data(net)
    seen: list[dict] = []
    original = workspace_acl.configure_tree

    async def spy(name, path):
        seen.append(json.loads(workspace._marker("p1").read_text()))
        await original(name, path)

    workspace_acl.configure_tree = spy
    try:
        run(workspace.ensure("p1"))
    finally:
        workspace_acl.configure_tree = original

    state = seen[0]
    host = ensure_workspace("p1")
    assert state["stage"] == "published"
    assert state["source_ino"] == host.stat().st_ino and state["source_dev"] == host.stat().st_dev


# --- M2: Auslesen wird gegen ein zweites Auslesen geprüft ------------------------------------------------------------------


def test_m2_abweichender_zweiter_strom_veroeffentlicht_nichts(net) -> None:
    run(container.launch("p1", container.Limits()))
    _with_data(net)
    net.tar_break_second = True                         # jemand schreibt zwischen den beiden Strömen

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1"))

    assert exc.value.code == "vibe_workspace_migration_failed"
    assert not workspace._marker("p1").exists()          # nichts gestoppt/halb migriert
    assert not any(ensure_workspace("p1").iterdir())
    assert _device(net) is None
    assert net.containers[container.name_for("p1")]["running"] is True
    net.tar_break_second = False
    assert run(workspace.ensure("p1")) == "migrated"  # Wiederholung klappt


def test_m2_gleicher_baum_wird_erkannt_und_abweichung_nicht(tmp_path) -> None:
    from backend import workspace_verify as wm

    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        (root / "src").mkdir(parents=True)
        (root / "src" / "x.txt").write_text("1", encoding="utf-8")
        (root / "link").symlink_to("src/x.txt")
    assert wm.same_tree(a, b)

    (b / "src" / "x.txt").write_text("2", encoding="utf-8")  # gleiche Größe, anderer Inhalt
    assert not wm.same_tree(a, b)
    (b / "src" / "x.txt").write_text("1", encoding="utf-8")
    (b / "link").unlink()
    (b / "link").symlink_to("anderswo")
    assert not wm.same_tree(a, b)
    (b / "link").unlink()
    (b / "link").symlink_to("src/x.txt")
    (b / "extra").write_text("e", encoding="utf-8")
    assert not wm.same_tree(a, b)


def test_m2_unterschiedliche_dateimodi_werden_erkannt(tmp_path) -> None:
    from backend import workspace_verify as wm

    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        root.mkdir()
        (root / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        os.chmod(root / "run.sh", 0o755)
    assert wm.same_tree(a, b)

    os.chmod(b / "run.sh", 0o644)
    assert not wm.same_tree(a, b)


def test_m2_fifo_wird_nie_geoeffnet_und_verglichen(tmp_path) -> None:
    """Ein FIFO würde beim Lesen ewig blockieren; er wird nur nach Art verglichen."""
    from backend import workspace_verify as wm

    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        root.mkdir()
        os.mkfifo(root / "pipe")
    assert wm.same_tree(a, b)                                # kein Hänger

    (b / "pipe").unlink()
    (b / "pipe").write_text("", encoding="utf-8")             # Art unterscheidet sich
    assert not wm.same_tree(a, b)


def test_m2_erweiterte_attribute_werden_verglichen(tmp_path) -> None:
    from backend import workspace_verify as wm

    a, b = tmp_path / "a", tmp_path / "b"
    for root in (a, b):
        root.mkdir()
        (root / "f").write_text("x", encoding="utf-8")
    try:
        os.setxattr(a / "f", "user.vibe", b"1")
    except OSError:
        pytest.skip("Dateisystem ohne user-xattr")
    assert not wm.same_tree(a, b)
    os.setxattr(b / "f", "user.vibe", b"1")
    assert wm.same_tree(a, b)
