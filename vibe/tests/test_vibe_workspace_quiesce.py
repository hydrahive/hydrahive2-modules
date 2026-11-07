"""M1 aus dem Review vom 6.11.: Agentenläufe ruhigstellen (Session-Guard des Kerns) – zweiter Teil zu
test_vibe_workspace_locking.py."""

from __future__ import annotations

import asyncio

import pytest
from _hh_isolation import remove_test_tree
from hydrahive.projects._paths import ensure_workspace

from backend import (
    container,
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


def _with_data(fake) -> None:
    fake.exec_answers["find /work"] = (0, "/work/src/App.tsx\n")


def _device(fake) -> dict | None:
    return fake.containers[container.name_for("p1")]["devices"].get(workspace.DEVICE)


# --- M1: Ruhigstellen ------------------------------------------------------------------------------------------------


class _Rows:
    """Ersatz für die Sitzungstabelle: Einträge (id, agent_id, project_id)."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str | None]] = []

    def install(self, monkeypatch) -> None:
        monkeypatch.setattr(workspace_lock, "_session_rows", lambda: list(self.rows))


@pytest.fixture
def table(monkeypatch):
    rows = _Rows()
    rows.install(monkeypatch)
    return rows


def test_m1_waehrend_der_migration_startet_kein_agentenlauf(net, table) -> None:
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    _with_data(net)
    table.rows = [("s1", "agent-1", "p1")]
    outcome: dict = {}

    async def probe():
        await asyncio.sleep(0.01)  # mitten im (verzögerten) Pull
        try:
            async with concurrency.session_run_guard("s1"):
                outcome["started"] = True
        except concurrency.SessionAlreadyRunning:
            outcome["blocked"] = True

    async def scenario():
        await asyncio.gather(workspace.ensure("p1", agent_id="agent-1"), probe())
        async with concurrency.session_run_guard("s1"):  # danach ist der Guard wieder frei
            outcome["free_after"] = True

    run(scenario())

    assert outcome == {"blocked": True, "free_after": True}


def test_m1_sitzung_waehrend_der_pruefung_wird_noch_erfasst(net, table, monkeypatch) -> None:
    """Review 2: Eine Sitzung, die nach der letzten Abfrage entsteht und sofort läuft, wurde nicht erfasst."""
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    table.rows = [("s1", "agent-1", "p1")]
    real_running = container.running
    held = {}

    async def running_and_new_session(pid):
        table.rows.append(("s2", "agent-1", "p1"))           # neue Sitzung ...
        cm = concurrency.session_run_guard("s2")             # ... deren Lauf sofort startet
        await cm.__aenter__()
        held["cm"] = cm
        return await real_running(pid)

    monkeypatch.setattr(container, "running", running_and_new_session)

    async def scenario():
        try:
            await workspace.ensure("p1", agent_id="agent-1")
        finally:
            if "cm" in held:
                await held["cm"].__aexit__(None, None, None)

    with pytest.raises(container.VibeError) as exc:
        run(scenario())

    assert exc.value.code == "vibe_busy"
    assert not [c for c in net.calls if c[:1] == ["stop"]]


def test_m1_aktive_sitzung_jenseits_von_500_wird_erkannt(net, table) -> None:
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    table.rows = [(f"s{i}", "agent-1", "p1") for i in range(501)]

    async def scenario():
        async with concurrency.session_run_guard("s500"):    # die 501. (älteste) Sitzung läuft
            await workspace.ensure("p1", agent_id="agent-1")

    with pytest.raises(container.VibeError) as exc:
        run(scenario())

    assert exc.value.code == "vibe_busy"
    assert not [c for c in net.calls if c[:1] == ["stop"]]


def test_m1_laufender_agent_stoppt_den_container_nie(net, table) -> None:
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    table.rows = [("s1", "agent-1", "p1")]

    async def scenario():
        async with concurrency.session_run_guard("s1"):
            with pytest.raises(container.VibeError) as exc:
                await workspace.ensure("p1", agent_id="agent-1")
            return exc.value.code

    assert run(scenario()) == "vibe_busy"
    assert not [c for c in net.calls if c[:1] == ["stop"]]
    assert net.containers[container.name_for("p1")]["running"] is True


def test_m1_entkoppelter_run_task_ohne_guard_zaehlt_als_laufend(net, table) -> None:
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    table.rows = [("s1", "agent-1", "p1")]

    async def scenario():
        task = asyncio.create_task(asyncio.sleep(5))
        concurrency.register_task("s1", task)
        try:
            with pytest.raises(container.VibeError) as exc:
                await workspace.ensure("p1", agent_id="agent-1")
            return exc.value.code
        finally:
            task.cancel()
            concurrency.unregister_task("s1")

    assert run(scenario()) == "vibe_busy"
