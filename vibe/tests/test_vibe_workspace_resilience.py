"""Review 6, Teil 1: Fehler beim Auslesen stellen den Ausgangszustand IMMER wieder her (Dev-Server, Container, Marker)."""

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
    workspace_lock,
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


@pytest.fixture
def net(fake_incus, monkeypatch):
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    run(network.ensure_network())
    return fake_incus


def _calls(net, word: str) -> list[str]:
    return [" ".join(c) for c in net.calls if word in c]


# --- HOCH: jede Ausnahme beim Auslesen stellt den Ausgangszustand her ------------------------------------------------


@pytest.mark.parametrize(
    "boom",
    [IncusError("incus_timeout"), IncusError("incus_missing"), OSError("Platte voll"), RuntimeError("unerwartet")],
    ids=["timeout", "incus_fehlt", "oserror", "unerwartet"],
)
def test_fehler_beim_auslesen_eines_laufenden_containers_stellt_den_dev_server_wieder_her(net, monkeypatch, boom) -> None:
    run(container.launch("p1", container.Limits()))

    async def failing(*_a, **_k):
        raise boom

    monkeypatch.setattr(incus, "run_to_file", failing)

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1", agent_id=""))

    assert exc.value.code == "vibe_workspace_migration_failed"
    systemd = _calls(net, "systemctl")
    assert any("stop vibe-dev.service" in c for c in systemd)
    assert any("start vibe-dev.service" in c for c in systemd)          # wieder angeschaltet
    assert net.containers[container.name_for("p1")]["running"] is True
    assert not workspace._marker("p1").exists()
    assert not any(ensure_workspace("p1").iterdir())


def test_fehler_beim_auslesen_eines_gestoppten_containers_stoppt_ihn_wieder(net, monkeypatch) -> None:
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))

    async def failing(*_a, **_k):
        raise IncusError("incus_timeout")

    monkeypatch.setattr(incus, "run_to_file", failing)

    with pytest.raises(container.VibeError):
        run(workspace.ensure("p1", agent_id=""))

    assert net.containers[container.name_for("p1")]["running"] is False
    assert not workspace._marker("p1").exists()


def test_abbruch_des_tasks_stellt_den_ausgangszustand_her(net, monkeypatch) -> None:
    run(container.launch("p1", container.Limits()))

    async def hanging(*_a, **_k):
        await asyncio.sleep(30)

    monkeypatch.setattr(incus, "run_to_file", hanging)

    async def scenario():
        task = asyncio.create_task(workspace.ensure("p1", agent_id=""))
        await asyncio.sleep(0.2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    run(scenario())

    assert any("start vibe-dev.service" in c for c in _calls(net, "systemctl"))
    assert not workspace._marker("p1").exists()
    assert not workspace_lock._lock_file("p1").is_dir()


def test_fehler_im_dev_server_stopp_ist_kein_abbruchgrund_aber_lesen_scheitert_sauber(net, monkeypatch) -> None:
    run(container.launch("p1", container.Limits()))
    net.tar_files = {"a": b"1"}
    net.tar_break_second = True

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1", agent_id=""))

    assert exc.value.code == "vibe_workspace_migration_failed"


def test_unerwartete_ausnahme_beim_auslesen_wird_zu_vibe_error_und_stellt_her(net, monkeypatch) -> None:
    """Der allgemeine Zweig: eine Ausnahme, die weder VibeError noch Abbruch ist, wird übersetzt UND aufgeräumt."""
    from backend import workspace_read

    run(container.launch("p1", container.Limits()))

    async def kaputt(*_a, **_k):
        raise ZeroDivisionError("unerwartet")

    monkeypatch.setattr(workspace_read, "read_work", kaputt)
    from backend import workspace_begin

    monkeypatch.setattr(workspace_begin, "read_work", kaputt)

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure("p1", agent_id=""))

    assert exc.value.code == "vibe_workspace_migration_failed"
    assert any("start vibe-dev.service" in c for c in _calls(net, "systemctl"))
    assert not workspace._marker("p1").exists()
