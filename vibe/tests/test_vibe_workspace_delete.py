"""M1 aus dem Review vom 6.11., Teil 4: Löschen eines Projekts stoppt alle Läufe (auch von Spezialisten) und hält sie fest."""

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


def test_m1_loeschen_stoppt_alle_laeufe_des_projekts_auch_von_spezialisten(
    setup_test_env, db_ready, fake_incus, monkeypatch
) -> None:
    """Review 3: `_drop_sessions` kannte nur den Haupt-Agenten und nur 500 Sitzungen."""
    from hydrahive.db import sessions as sessions_db
    from hydrahive.projects import execution
    from hydrahive.runner import concurrency

    from backend import projects, state

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    out = run(projects.create(admin="boss", name="Spez", model="claude-sonnet-4-6"))
    pid, aid = out["project_id"], out["agent_id"]
    spec = sessions_db.create(agent_id="spec-9", user_id="boss", project_id=pid, title="Spezialist")
    ran = {}

    async def scenario():
        async def worker():
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                ran["abgebrochen"] = True
                raise

        task = asyncio.create_task(worker())
        await asyncio.sleep(0)                                # Worker läuft an und wartet im sleep(30)
        concurrency.register_task(spec.id, task)
        try:
            await projects.remove(pid, owner="boss")
        finally:
            concurrency.unregister_task(spec.id)
            task.cancel()

    run(scenario())

    assert ran == {"abgebrochen": True}
    assert state.get_row(pid) is None and not run(container.exists(pid))
    assert aid


def test_m1_loeschen_haelt_die_guards_bis_alles_weg_ist(setup_test_env, db_ready, fake_incus, monkeypatch) -> None:
    from hydrahive.db import sessions as sessions_db
    from hydrahive.projects import execution
    from hydrahive.runner import concurrency

    from backend import projects

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    out = run(projects.create(admin="boss", name="Halten", model="claude-sonnet-4-6"))
    pid = out["project_id"]
    spec = sessions_db.create(agent_id="spec-8", user_id="boss", project_id=pid, title="S")
    seen = {}
    real_remove = container.remove

    async def spy(project_id):
        try:
            async with concurrency.session_run_guard(spec.id):
                seen["startete"] = True
        except concurrency.SessionAlreadyRunning:
            seen["gesperrt"] = True
        await real_remove(project_id)

    monkeypatch.setattr(container, "remove", spy)

    run(projects.remove(pid, owner="boss"))

    assert seen == {"gesperrt": True}


def test_nachzuegler_ensure_nach_dem_loeschen_legt_nichts_neu_an(
    setup_test_env, db_ready, fake_incus, monkeypatch
) -> None:
    """Review 4 (R4-M2/M3): `ensure()` prüfte das Projekt nicht unter der Sperre; `host_path()` legte den gelöschten
    Workspace per `ensure_workspace()` einfach neu an."""
    from hydrahive.projects import execution
    from hydrahive.projects._paths import workspace_path

    from backend import projects, workspace

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    out = run(projects.create(admin="boss", name="Nachzug", model="claude-sonnet-4-6"))
    pid, aid = out["project_id"], out["agent_id"]
    run(projects.remove(pid, owner="boss"))
    assert not workspace_path(pid).exists()

    with pytest.raises(container.VibeError) as exc:
        run(workspace.ensure(pid, agent_id=aid))

    assert exc.value.code == "vibe_project_not_found"
    assert not workspace_path(pid).exists()                          # nicht neu angelegt
    assert not workspace_lock._lock_file(pid).exists()               # auch keine Sperrdatei zurückgelassen


def test_nachzuegler_attach_new_nach_dem_loeschen_legt_nichts_neu_an(
    setup_test_env, db_ready, fake_incus, monkeypatch
) -> None:
    from hydrahive.projects import execution
    from hydrahive.projects._paths import workspace_path

    from backend import projects, workspace

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    out = run(projects.create(admin="boss", name="Nachzug2", model="claude-sonnet-4-6"))
    pid = out["project_id"]
    run(projects.remove(pid, owner="boss"))

    with pytest.raises(container.VibeError) as exc:
        run(workspace.attach_new(pid))

    assert exc.value.code == "vibe_project_not_found"
    assert not workspace_path(pid).exists()


def test_ensure_fuer_ein_lebendes_projekt_funktioniert_weiter(
    setup_test_env, db_ready, fake_incus, monkeypatch
) -> None:
    from hydrahive.projects import execution

    from backend import projects, workspace

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    monkeypatch.setattr(workspace_acl, "_run", lambda _args: None)
    out = run(projects.create(admin="boss", name="Lebt", model="claude-sonnet-4-6"))

    assert run(workspace.ensure(out["project_id"], agent_id=out["agent_id"])) == "ready"
