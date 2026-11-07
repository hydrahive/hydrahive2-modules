"""M1 aus dem Review vom 6.11., Teil 3: ALLE Sitzungen des Projekts (auch Spezialisten) ruhigstellen, Löschen darunter."""

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


# --- M1: Ruhigstellen ---


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


def test_m1_spezialist_des_projekts_wird_ruhiggestellt(net, table) -> None:
    """Review 3: Sitzungen anderer Agenten (Spezialisten), die auf das Projekt zeigen, liefen ungebremst weiter."""
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    table.rows = [("s-main", "agent-1", "p1"), ("s-spec", "spec-1", "p1"), ("s-fremd", "other", "p2")]

    async def scenario():
        async with concurrency.session_run_guard("s-spec"):          # Spezialist arbeitet gerade
            await workspace.ensure("p1", agent_id="agent-1")

    with pytest.raises(container.VibeError) as exc:
        run(scenario())

    assert exc.value.code == "vibe_busy"
    assert not [c for c in net.calls if c[:1] == ["stop"]]


def test_m1_fremde_projekte_stoeren_nicht(net, table) -> None:
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    _with_data(net)
    table.rows = [("s-main", "agent-1", "p1"), ("s-fremd", "other", "p2")]

    async def scenario():
        async with concurrency.session_run_guard("s-fremd"):         # läuft in einem ANDEREN Projekt
            return await workspace.ensure("p1", agent_id="agent-1")

    assert run(scenario()) == "migrated"


def test_m1_neue_sitzung_zwischen_auslesen_und_stop_wird_bemerkt(net, table, monkeypatch) -> None:
    """Review 3: `refresh()` lief nur vor der Prüfung; ein Lauf, der danach startet, verlor beim Stop seine Arbeit."""
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    _with_data(net)
    table.rows = [("s-main", "agent-1", "p1")]
    held = {}
    real_stop = workspace_migration._stop_and_isolate

    async def late_session(name):
        raise AssertionError("darf nicht mehr erreicht werden")

    # Direkt NACH dem Auslesen (erste Tar-Ströme laufen) entsteht eine neue Sitzung und startet sofort.
    original = net.run_to_file

    async def after_streams(*a, **k):
        result = await original(*a, **k)
        if net.tar_count == 2 and "s-neu" not in held:
            table.rows.append(("s-neu", "spec-2", "p1"))
            cm = concurrency.session_run_guard("s-neu")
            await cm.__aenter__()
            held["s-neu"] = cm
        return result

    monkeypatch.setattr("backend.incus.run_to_file", after_streams)
    monkeypatch.setattr(workspace_migration, "_stop_and_isolate", late_session)

    async def scenario():
        try:
            await workspace.ensure("p1", agent_id="agent-1")
        finally:
            if "s-neu" in held:
                await held["s-neu"].__aexit__(None, None, None)

    with pytest.raises(container.VibeError) as exc:
        run(scenario())

    del real_stop
    assert exc.value.code == "vibe_busy"
    assert net.containers[container.name_for("p1")]["running"] is True       # nichts gestoppt
    assert not any(ensure_workspace("p1").iterdir())                          # nichts veröffentlicht


def test_m1_guards_bleiben_bis_nach_dem_stop_gehalten(net, table, monkeypatch) -> None:
    from hydrahive.runner import concurrency

    run(container.launch("p1", container.Limits()))
    _with_data(net)
    table.rows = [("s-main", "agent-1", "p1")]
    seen = {}
    real = workspace_migration._stop_and_isolate

    async def spy(name):
        try:
            async with concurrency.session_run_guard("s-main"):
                seen["gestartet_beim_stop"] = True
        except concurrency.SessionAlreadyRunning:
            seen["gesperrt_beim_stop"] = True
        await real(name)

    monkeypatch.setattr(workspace_migration, "_stop_and_isolate", spy)

    run(workspace.ensure("p1", agent_id="agent-1"))

    assert seen == {"gesperrt_beim_stop": True}
