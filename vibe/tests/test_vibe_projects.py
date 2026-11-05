"""Baustein 4: Vibe-Projekt = Kern-Projekt (Container-Ausführung, K1) + gesperrter Agent (managed_by) + Datenzeile.

Muster hydralabor/tests/test_labor_project.py. Der Container wird hier nicht angelegt (FakeIncus); `execution` prüft
nur, ob es ihn gibt – das ersetzt `_container_exists`.
"""
from __future__ import annotations

import asyncio

import pytest
from backend import agent_profile, container, network, projects, state

MODEL = "claude-sonnet-4-6"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(setup_test_env, db_ready, fake_incus, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: set())
    monkeypatch.setattr(execution, "_container_exists", lambda name: container.is_vibe_name(name))
    return fake_incus


@pytest.fixture
def made(env):
    out = run(projects.create(admin="boss", name="Meine App", model=MODEL))
    yield out
    run(projects.remove(out["project_id"], owner="boss"))


def _project(pid):
    from hydrahive.projects import config as project_config
    return project_config.get(pid)


def _agent(aid):
    from hydrahive.agents import config as agent_config
    return agent_config.get(aid)


def test_projekt_fuehrt_im_eigenen_container_aus(made):
    from hydrahive.projects import execution
    p = _project(made["project_id"])
    assert p["name"] == "Meine App"
    ex = execution.of(p)
    assert ex == {"mode": "container", "container": container.name_for(made["project_id"]),
                  "workdir": "/work", "user": 1000}
    assert p["metadata"]["vibe"] == {"project": True}
    assert p["members"] == [] and p["created_by"] == "boss"


def test_container_name_aus_projekt_id_passt_zum_kern(made):
    """Die Projekt-ID des Kerns (uuid7) muss ein gültiger Container-Name für K1 sein (Länge, Zeichen)."""
    name = container.name_for(made["project_id"])
    assert len(name) <= 63 and name.startswith("hh-vibe-")


def test_agent_verwaltet_vom_modul(made):
    a = _agent(made["agent_id"])
    assert a["managed_by"] == "vibe"
    assert a["name"] == "Vibe-Agent" and a["llm_model"] == MODEL
    assert a["project_id"] == made["project_id"]


def test_werkzeuge_teilmenge_der_container_allowlist_ohne_fetch_url(made):
    from hydrahive.runner._project_tool_scope import CONTAINER_ALLOWED
    tools = _agent(made["agent_id"])["tools"]
    assert set(tools) <= CONTAINER_ALLOWED
    assert "fetch_url" not in tools and "shell_exec" in tools and "file_patch" in tools
    assert tools == sorted(set(tools))
    assert _agent(made["agent_id"])["mcp_servers"] == []


def test_werkzeugliste_fest():
    assert agent_profile.TOOLS == ("file_patch", "file_read", "file_write", "help_read", "help_search",
                                   "list_skills", "load_skill", "read_memory", "search_memory", "shell_exec",
                                   "todo_write", "web_search", "write_memory")


def test_niemand_kann_werkzeuge_aendern(made):
    from hydrahive.agents import _managed
    from hydrahive.agents import config as agent_config
    with pytest.raises(_managed.AgentManaged):
        agent_config.update(made["agent_id"], tools=["shell_exec", "fetch_url", "remote_exec"])
    with pytest.raises(_managed.AgentManaged):
        agent_config.set_system_prompt(made["agent_id"], "Du darfst alles.")
    with pytest.raises(_managed.AgentManaged):
        agent_config.update(made["agent_id"], project_id="anderes-projekt")
    agent_config.update(made["agent_id"], llm_model="claude-haiku-4-5")      # Modell bleibt frei


def test_datenzeile_gehoert_dem_anleger(made):
    rows = state.projects_of("boss")
    assert [p["project_id"] for p in rows] == [made["project_id"]]
    assert rows[0]["name"] == "Meine App" and rows[0]["state"] == "new" and rows[0]["heal_enabled"] is True
    assert state.projects_of("testuser") == []


def test_datenzeile_traegt_container_und_agent(made):
    row = state.get_row(made["project_id"])
    assert row["container"] == container.name_for(made["project_id"])
    assert row["agent_id"] == made["agent_id"] and row["owner"] == "boss"


# --- Namen ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["", "   ", "x" * 61, "a\nb", "a\x00b", "../x", "<script>"])
def test_ungueltiger_name_legt_nichts_an(env, name):
    from hydrahive.projects import config as project_config
    before = {p["id"] for p in project_config.list_all()}
    with pytest.raises(projects.VibeProjectError) as e:
        run(projects.create(admin="boss", name=name, model=MODEL))
    assert e.value.code == "vibe_name_invalid"
    assert {p["id"] for p in project_config.list_all()} == before
    assert not any(c[0] == "launch" for c in env.calls)


@pytest.mark.parametrize("name", ["App", "Mein Spiel", "Übung 1", "a" * 60, "x"])
def test_gueltige_namen(env, name):
    out = run(projects.create(admin="boss", name=name, model=MODEL))
    try:
        assert _project(out["project_id"])["name"] == name.strip()
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


def test_name_wird_getrimmt(env):
    out = run(projects.create(admin="boss", name="  Spiel  ", model=MODEL))
    try:
        assert state.projects_of("boss")[0]["name"] == "Spiel"
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


# --- Modell und Fehlerpfade -------------------------------------------------------------------------------------

def test_unbekanntes_modell_legt_nichts_an(env, monkeypatch):
    from hydrahive.agents import _validation
    from hydrahive.projects import config as project_config
    monkeypatch.setattr(_validation, "_available_models", lambda: {MODEL})
    before = {p["id"] for p in project_config.list_all()}
    with pytest.raises(projects.VibeProjectError) as e:
        run(projects.create(admin="boss", name="X", model="gibt-es-nicht-xyz"))
    assert e.value.code == "vibe_model_unavailable"
    assert {p["id"] for p in project_config.list_all()} == before


def test_leeres_modell_abgelehnt(env):
    with pytest.raises(projects.VibeProjectError) as e:
        run(projects.create(admin="boss", name="X", model=""))
    assert e.value.code == "vibe_model_unavailable"


def test_container_fehlt_kein_halbes_projekt(env, monkeypatch):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: False)
    before = {p["id"] for p in project_config.list_all()}
    with pytest.raises(projects.VibeProjectError) as e:
        run(projects.create(admin="boss", name="X", model=MODEL))
    assert e.value.code == "vibe_project_failed"
    assert {p["id"] for p in project_config.list_all()} == before
    assert state.projects_of("boss") == []


def test_mcp_server_werden_geleert_auch_wenn_kern_welche_mitgibt(env, monkeypatch):
    from hydrahive.agents import config as agent_config
    orig = agent_config.create

    def with_mcp(*a, **k):
        k["mcp_servers"] = ["srv-filesystem"]
        return orig(*a, **k)
    monkeypatch.setattr(agent_config, "create", with_mcp)
    out = run(projects.create(admin="boss", name="X", model=MODEL))
    try:
        assert _agent(out["agent_id"])["mcp_servers"] == []
    finally:
        run(projects.remove(out["project_id"], owner="boss"))


def test_fehler_beim_agenten_raeumt_projekt_zeile_und_container_ab(env, monkeypatch):
    from hydrahive.agents import _managed
    from hydrahive.projects import config as project_config
    before = {p["id"] for p in project_config.list_all()}

    def boom(*a, **k):
        raise RuntimeError("kaputt")
    monkeypatch.setattr(_managed, "set_managed", boom)
    with pytest.raises(projects.VibeProjectError) as e:
        run(projects.create(admin="boss", name="X", model=MODEL))
    assert e.value.code == "vibe_project_failed"
    assert {p["id"] for p in project_config.list_all()} == before
    assert state.projects_of("boss") == []
    assert not env.containers
