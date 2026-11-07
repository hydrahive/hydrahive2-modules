"""Review 7: Abbruch im Entpack-Thread, Fehler beim Speichern des Markers und eine BESTÄTIGTE Wiederherstellung."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import (
    container,
    network,
    workspace,
    workspace_acl,
    workspace_begin,
    workspace_mount,
    workspace_tar,
)


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
    workspace_mount.clear_migration("p1")


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    run(network.ensure_network())
    return fake_incus


def _calls(net, word: str) -> list[str]:
    return [" ".join(c) for c in net.calls if word in c]


def _name() -> str:
    return container.name_for("p1")


# --- BLOCKER 1: Abbruch, während der Entpack-Thread noch läuft ----------------------------------------------------------


def test_abbruch_wartet_auf_den_entpack_thread_bevor_aufgeraeumt_wird(net, monkeypatch) -> None:
    """Der Thread darf nach dem Aufräumen nichts mehr anlegen (sonst bleibt Staging zurück)."""
    run(container.launch("p1", container.Limits()))
    started, state = threading.Event(), {"done": False}

    def slow_extract(archive, target, cancel=None):
        started.set()
        while not cancel.is_set():
            time.sleep(0.01)
        time.sleep(0.3)                                     # arbeitet nach dem Abbruch noch kurz weiter …
        target.mkdir(parents=True, exist_ok=True)           # … und legt dabei Staging neu an (der Fehler aus Review 7)
        state["done"] = True
        raise container.VibeError("vibe_workspace_migration_failed")

    monkeypatch.setattr(workspace_tar, "extract", slow_extract)

    async def scenario():
        task = asyncio.create_task(workspace.ensure("p1", agent_id=""))
        while not started.is_set():
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert state["done"] is True                        # der Thread war schon fertig, als der Abbruch durchlief

    run(scenario())

    assert not workspace_mount.staging("p1").exists()
    assert not workspace_mount.marker("p1").exists()
    assert any("start vibe-dev.service" in c for c in _calls(net, "systemctl"))


def test_gesetztes_abbruchsignal_stoppt_das_entpacken_sofort(tmp_path) -> None:
    import io
    import tarfile

    archive = tmp_path / "x.tar"
    with tarfile.open(archive, "w") as tar:
        info = tarfile.TarInfo("f")
        info.size = 3
        tar.addfile(info, io.BytesIO(b"abc"))
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(container.VibeError):
        workspace_tar.extract(archive, tmp_path / "out", cancel)

    assert not (tmp_path / "out" / "work" / "f").exists()


# --- BLOCKER 2: Fehler beim Speichern des Zustands „pulled“ ---------------------------------------------------------------


@pytest.mark.parametrize("was_running", [True, False])
def test_fehler_beim_speichern_von_pulled_stellt_den_ausgangszustand_her(net, monkeypatch, was_running) -> None:
    run(container.launch("p1", container.Limits()))
    if not was_running:
        run(container.stop("p1"))

    def boom(*_a, **_k):
        raise OSError("Platte voll")

    real_save = workspace_begin._save
    monkeypatch.setattr(
        workspace_begin, "_save", lambda pid, state: boom() if state["stage"] == "pulled" else real_save(pid, state)
    )
    net.tar_files = {"a": b"1"}

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1", agent_id=""))

    assert exc.value.code == "vibe_workspace_migration_failed"
    assert net.containers[_name()]["running"] is was_running
    assert not workspace_mount.marker("p1").exists()
    assert not workspace_mount.staging("p1").exists()
    if was_running:
        assert any("start vibe-dev.service" in c for c in _calls(net, "systemctl"))
