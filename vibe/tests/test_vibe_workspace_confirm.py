"""Review 7: Die Wiederherstellung nach einem Fehler wird BESTÄTIGT; sonst bleibt der Marker als Wiederanlaufhinweis."""

from __future__ import annotations

import asyncio

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.containers.incus_client import IncusError
from hydrahive.projects._paths import ensure_workspace

from backend import (
    container,
    incus,
    network,
    workspace,
    workspace_acl,
    workspace_mount,
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


# --- BLOCKER 3: Wiederherstellung wird bestätigt, sonst bleibt der Marker -----------------------------------------------


def _read_fails(monkeypatch) -> None:
    async def failing(*_a, **_k):
        raise IncusError("incus_timeout")

    monkeypatch.setattr(incus, "run_to_file", failing)


def test_gescheitertes_stoppen_laesst_den_marker_als_wiederanlaufhinweis_stehen(net, monkeypatch) -> None:
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    _read_fails(monkeypatch)
    net.fail["stop " + _name()] = "kaputt"

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1", agent_id=""))

    assert workspace_mount.marker("p1").exists()                       # ohne Marker wüsste niemand, dass aufzuräumen ist
    assert not workspace_mount.staging("p1").exists()


def test_gescheiterter_dev_server_start_laesst_den_marker_stehen(net, monkeypatch) -> None:
    run(container.launch("p1", container.Limits()))
    _read_fails(monkeypatch)
    net.fail["start vibe-dev.service"] = "kaputt"

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1", agent_id=""))

    assert workspace_mount.marker("p1").exists()


def test_inzwischen_gestoppter_container_wird_wieder_gestartet(net, monkeypatch) -> None:
    """Der Container lief ursprünglich, ist beim Fehler aber aus: der Ausgangszustand ist „läuft“."""
    run(container.launch("p1", container.Limits()))

    async def stop_then_fail(*_a, **_k):
        net.containers[_name()]["running"] = False
        raise IncusError("incus_timeout")

    monkeypatch.setattr(incus, "run_to_file", stop_then_fail)

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1", agent_id=""))

    assert net.containers[_name()]["running"] is True
    assert any("start vibe-dev.service" in c for c in _calls(net, "systemctl"))
    assert not workspace_mount.marker("p1").exists()


def test_abbruch_zwischen_start_und_merker_laesst_keinen_laufenden_container_zurueck(net, monkeypatch) -> None:
    """Ein ursprünglich gestoppter Container, der gerade gestartet wurde, wird auch bei Abbruch wieder gestoppt."""
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    real = container.running_name
    calls = {"n": 0}

    async def hanging_check(name):
        calls["n"] += 1
        if calls["n"] == 2:                                            # die Prüfung direkt nach `incus start`
            await asyncio.sleep(30)
        return await real(name)

    monkeypatch.setattr(container, "running_name", hanging_check)

    async def scenario():
        task = asyncio.create_task(workspace.ensure("p1", agent_id=""))
        while calls["n"] < 2:
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    run(scenario())

    assert net.containers[_name()]["running"] is False
    assert not workspace_mount.marker("p1").exists()
