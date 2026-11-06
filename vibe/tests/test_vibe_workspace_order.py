"""M1 aus dem Review vom 6.11., Teil 5: Reihenfolge – erst ruhigstellen, dann auslesen/stoppen."""

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
    workspace_migration,
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


def test_m1_haupt_agent_ohne_projektbezug_wird_ebenfalls_ruhiggestellt(net, table) -> None:
    """Eine Sitzung des Projekt-Agenten ohne `project_id` zählt weiter dazu (alte/umgehängte Sitzungen)."""
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    table.rows = [("s-alt", "agent-1", None)]

    async def scenario():
        async with concurrency.session_run_guard("s-alt"):
            await workspace.ensure("p1", agent_id="agent-1")

    with pytest.raises(container.VibeError) as exc:
        run(scenario())

    assert exc.value.code == "vibe_busy"


def test_m1_laufender_lauf_verhindert_schon_das_auslesen(net, table) -> None:
    """Der Lauf wird VOR dem ersten Auslesen erkannt – es wird nichts gestoppt und nichts gelesen."""
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    _with_data(net)
    table.rows = [("s1", "agent-1", "p1")]

    async def scenario():
        async with concurrency.session_run_guard("s1"):
            await workspace.ensure("p1", agent_id="agent-1")

    with pytest.raises(container.VibeError):
        run(scenario())

    assert net.tar_count == 0
    assert not [c for c in net.calls if "systemctl" in c]           # Dev-Server auch nicht angefasst


def test_m1_lauf_der_waehrend_des_auslesens_startet_bricht_vor_dem_stop_ab(net, table, monkeypatch) -> None:
    """Zusätzlich zur Prüfung vor dem Stop: `before_stop` wird auch VOR dem Start/Auslesen gerufen."""
    run(container.launch("p1", container.Limits()))
    run(container.stop("p1"))
    _with_data(net)
    table.rows = [("s1", "agent-1", "p1")]
    order: list[str] = []
    real = workspace_migration._begin

    async def spy(project_id, name, state, before_stop):
        async def traced():
            order.append("before_stop")
            await before_stop()

        real_start = net.run

        async def run_spy(*a, **k):
            if list(a[:1]) == ["start"]:
                order.append("start")
            return await real_start(*a, **k)

        monkeypatch.setattr(workspace_migration.incus, "run", run_spy)
        return await real(project_id, name, state, traced)

    monkeypatch.setattr(workspace_migration, "_begin", spy)

    run(workspace.ensure("p1", agent_id="agent-1"))

    assert order[:2] == ["before_stop", "start"]            # erst ruhigstellen, dann den Container starten
