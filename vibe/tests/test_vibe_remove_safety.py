from __future__ import annotations

import asyncio

import pytest

from backend import container, network, projects, state

MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution

    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(
        execution, "_container_exists", lambda name: container.is_vibe_name(name)
    )
    return fake_incus


def _project(project_id):
    from hydrahive.projects import config as project_config

    return project_config.get(project_id)


def test_containerfehler_behaelt_hostprojekt_und_ist_wiederholbar(env):
    out = run(projects.create(admin="boss", name="Sicher", model=MODEL))
    project_id = out["project_id"]
    env.fail[f"delete {container.name_for(project_id)}"] = "incus kaputt"

    with pytest.raises(container.VibeError) as exc:
        run(projects.remove(project_id, owner="boss"))

    assert exc.value.code == "vibe_container_remove_failed"
    assert _project(project_id) is not None and state.get_row(project_id) is not None
    assert container.name_for(project_id) in env.containers
    env.fail.clear()
    run(projects.remove(project_id, owner="boss"))
    assert _project(project_id) is None and state.get_row(project_id) is None


def test_hostprojekt_wird_erst_nach_containerentfernung_geloescht(env, monkeypatch):
    from hydrahive.projects import config as project_config

    out = run(projects.create(admin="boss", name="Reihenfolge", model=MODEL))
    project_id = out["project_id"]
    original = project_config.delete

    def checked_delete(pid):
        assert container.name_for(project_id) not in env.containers
        return original(pid)

    monkeypatch.setattr(project_config, "delete", checked_delete)
    run(projects.remove(project_id, owner="boss"))
