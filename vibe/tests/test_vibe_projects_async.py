"""Baustein 4: create/remove müssen innerhalb des Servers (laufende Ereignisschleife) funktionieren.

Befund 5.11.: Eine synchrone Hülle mit asyncio.run() wirft im Server „cannot be called from a running event loop“.
Die übrigen Tests riefen sie von außen auf und blieben deshalb grün. Hier läuft alles in EINER Schleife wie im Betrieb.
"""
from __future__ import annotations

import asyncio
import inspect

import pytest
from backend import container, network, projects, state

MODEL = "claude-sonnet-4-6"


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(container, "_ubuntu_version", lambda: "24.04")
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    return fake_incus


def test_create_und_remove_sind_coroutinen():
    assert inspect.iscoroutinefunction(projects.create)
    assert inspect.iscoroutinefunction(projects.remove)


def test_anlegen_und_entfernen_in_einer_laufenden_schleife(env):
    async def ablauf():
        out = await projects.create(admin="boss", name="Im Server", model=MODEL)
        assert state.get_row(out["project_id"]) is not None
        await projects.remove(out["project_id"], owner="boss")
        return out
    out = asyncio.run(ablauf())
    assert state.get_row(out["project_id"]) is None and not env.containers


def test_zwei_projekte_gleichzeitig_in_einer_schleife(env):
    async def ablauf():
        a, b = await asyncio.gather(projects.create(admin="boss", name="A", model=MODEL),
                                    projects.create(admin="boss", name="B", model=MODEL))
        assert a["project_id"] != b["project_id"]
        assert {r["project_id"] for r in map(state.get_row, (a["project_id"], b["project_id"]))} == \
            {a["project_id"], b["project_id"]}
        await asyncio.gather(projects.remove(a["project_id"], owner="boss"), projects.remove(b["project_id"], owner="boss"))
    asyncio.run(ablauf())
    assert not env.containers and network.NET not in env.networks


def test_fehler_in_der_schleife_raeumt_ab_und_meldet_code(env, monkeypatch):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: False)
    before = {p["id"] for p in project_config.list_all()}

    async def ablauf():
        with pytest.raises(projects.VibeProjectError) as e:
            await projects.create(admin="boss", name="X", model=MODEL)
        return e.value.code
    assert asyncio.run(ablauf()) == "vibe_project_failed"
    assert {p["id"] for p in project_config.list_all()} == before and not env.containers
