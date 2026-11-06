"""H2 und M1 aus dem Review vom 6.11.: ein Vorgang je Projekt (Sperre) und Agentenläufe ruhigstellen."""

from __future__ import annotations

import asyncio
import fcntl
import os
from pathlib import Path

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import container, network, workspace, workspace_acl, workspace_lock


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


# --- H2: ein Vorgang je Projekt ------------------------------------------------------------------------------------


def test_h2_parallele_ensure_wandern_nur_einmal(net) -> None:
    run(container.launch("p1", container.Limits()))
    _with_data(net)

    async def both():
        return await asyncio.gather(workspace.ensure("p1"), workspace.ensure("p1"), return_exceptions=True)

    results = run(both())

    assert sorted(r for r in results if isinstance(r, str)) == ["migrated", "ready"]
    assert not [r for r in results if isinstance(r, BaseException)]
    assert net.tar_count == 2  # zwei Ströme zum Vergleich, nicht doppelt migriert
    adds = [c for c in net.calls if c[:3] == ["config", "device", "add"]]
    assert len(adds) == 1


def test_h2_zweiter_prozess_bekommt_vibe_busy(net) -> None:
    run(container.launch("p1", container.Limits()))
    fd = os.open(workspace_lock._lock_file("p1"), os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(container.VibeError) as exc:
            run(workspace.ensure("p1"))
    finally:
        os.close(fd)

    assert exc.value.code == "vibe_busy"
    assert net.tar_count == 0 and _device(net) is None


def test_h2_forget_raeumt_marker_aber_entlinkt_nie_die_sperrdatei(net) -> None:
    """Review 2: `forget` löschte die Sperrdatei auch dann, wenn jemand sie hielt → zweiter Halter auf neuer Inode."""
    run(container.launch("p1", container.Limits()))
    _with_data(net)
    run(workspace.ensure("p1"))

    async def scenario():
        async with workspace_lock.project("p1"):
            workspace.forget("p1")
            fd = os.open(workspace_lock._lock_file("p1"), os.O_CREAT | os.O_RDWR, 0o600)
            try:
                with pytest.raises(OSError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # gehalten → muss scheitern
            finally:
                os.close(fd)

    run(scenario())
    assert not workspace_mount_marker_dir("p1").exists()


def test_h2_sperre_erkennt_ausgetauschte_datei_und_versucht_erneut(net, monkeypatch) -> None:
    """Wird die Sperrdatei zwischen `open` und `flock` ersetzt, gilt die Sperre auf der toten Inode nicht."""
    real = workspace_lock.fcntl.flock
    state = {"first": True}

    def flaky(fd, op):
        if state["first"]:
            state["first"] = False
            path = workspace_lock._lock_file("p1")
            path.unlink()
            path.write_text("", encoding="utf-8")  # neue Inode unter demselben Namen
        return real(fd, op)

    monkeypatch.setattr(workspace_lock.fcntl, "flock", flaky)

    async def scenario():
        async with workspace_lock.project("p1"):
            fd = os.open(workspace_lock._lock_file("p1"), os.O_RDWR)
            try:
                with pytest.raises(OSError):
                    real(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)

    run(scenario())


def test_h2_loeschen_laeuft_unter_der_projektsperre(setup_test_env, db_ready, fake_incus, monkeypatch) -> None:
    """Ein zweiter Prozess, der gerade migriert, hält die Sperre: Löschen meldet `vibe_busy` und zerstört nichts."""
    from hydrahive.projects import execution

    from backend import projects, state

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    out = run(projects.create(admin="boss", name="Sperre", model="claude-sonnet-4-6"))
    pid = out["project_id"]
    fd = os.open(workspace_lock._lock_file(pid), os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(container.VibeError) as exc:
            run(projects.remove(pid, owner="boss"))
    finally:
        os.close(fd)

    assert exc.value.code == "vibe_busy"
    assert run(container.exists(pid)) and state.get_row(pid) is not None
    run(projects.remove(pid, owner="boss"))            # danach klappt es
    assert not workspace_lock._lock_file(pid).exists()  # beim endgültigen Löschen wird die Datei unter der Sperre entfernt


def workspace_mount_marker_dir(pid: str) -> Path:
    from backend import workspace_mount

    return workspace_mount._migration_path(pid)
