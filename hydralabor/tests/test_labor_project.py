"""Hydra-Labor L1 Schritt 3: Projekt mit Container-Ausführung + verwalteter Labor-Agent (PLAN-L1.md 4/5)."""
from __future__ import annotations

import pytest
from backend import agent_profile, container, lab_project

MODEL = "claude-sonnet-4-6"


@pytest.fixture
def made(setup_test_env, monkeypatch):
    """Legt das Labor-Projekt an (Container gilt als vorhanden) und räumt danach nur das Eigene ab."""
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: name == container.NAME)
    out = lab_project.create(admin="boss", model=MODEL)
    yield out
    lab_project.remove(out)


def _project(pid):
    from hydrahive.projects import config as project_config
    return project_config.get(pid)


def _agent(aid):
    from hydrahive.agents import config as agent_config
    return agent_config.get(aid)


def test_projekt_fuehrt_im_labor_container_aus(made):
    from hydrahive.projects import execution
    p = _project(made["project_id"])
    assert p["name"] == "Hydra-Labor"
    assert execution.of(p) == {"mode": "container", "container": "hh-labor", "workdir": "/work", "user": 1000}
    assert p["metadata"]["hydralabor"] == {"lab": True}
    assert p["members"] == [] and p["created_by"] == "boss"


def test_labor_agent_verwaltet_vom_modul(made):
    a = _agent(made["agent_id"])
    assert a["managed_by"] == "hydralabor"
    assert a["name"] == "Labor-Agent" and a["llm_model"] == MODEL
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


def test_prompt_aus_moduldatei(made):
    from hydrahive.agents import config as agent_config
    prompt = agent_config.get_system_prompt(made["agent_id"])
    assert prompt == agent_profile.system_prompt()
    for must in ("/work/hydrahive2", "/work/hydrahive2-modules", "Container", "Server", "Tests"):
        assert must in prompt


def test_nur_labor_skills(made):
    a = _agent(made["agent_id"])
    from hydrahive.skills.loader import list_for_agent
    names = {s.name for s in list_for_agent(a["id"], "boss", disabled=a.get("disabled_skills"),
                                            project_id=made["project_id"])}
    assert {"labor-review", "test", "debugging", "code-review"} <= names
    for gone in ("hh-review", "git-workflow", "finishing-development-branch", "project-management"):
        assert gone not in names


def test_niemand_kann_werkzeuge_aendern(made):
    from hydrahive.agents import _managed
    from hydrahive.agents import config as agent_config
    with pytest.raises(_managed.AgentManaged):
        agent_config.update(made["agent_id"], tools=["shell_exec", "fetch_url", "remote_exec"])
    with pytest.raises(_managed.AgentManaged):
        agent_config.set_system_prompt(made["agent_id"], "Du darfst alles.")
    agent_config.update(made["agent_id"], llm_model="claude-haiku-4-5")      # Modell bleibt frei


def test_entfernen_raeumt_projekt_und_agent(setup_test_env, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: True)
    out = lab_project.create(admin="boss", model=MODEL)
    lab_project.remove(out)
    assert _project(out["project_id"]) is None and _agent(out["agent_id"]) is None
    lab_project.remove(out)                                                    # zweimal: kein Fehler


def test_entfernen_nur_eigenes_projekt(setup_test_env, monkeypatch):
    from hydrahive.projects import config as project_config
    other = project_config.create("Fremd", members=[], llm_model=MODEL, created_by="boss")
    try:
        lab_project.remove({"project_id": other["id"], "agent_id": other["agent_id"]})
        assert _project(other["id"]) is not None and _agent(other["agent_id"]) is not None
    finally:
        project_config.delete(other["id"])


def test_container_fehlt_kein_halbes_projekt(setup_test_env, monkeypatch):
    from hydrahive.projects import config as project_config
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: False)
    before = {p["id"] for p in project_config.list_all()}
    with pytest.raises(container.LaborError) as e:
        lab_project.create(admin="boss", model=MODEL)
    assert e.value.code == "labor_project_failed"
    assert {p["id"] for p in project_config.list_all()} == before


def test_unbekanntes_modell(setup_test_env, monkeypatch):
    from hydrahive.projects import execution
    monkeypatch.setattr(execution, "_container_exists", lambda name: True)
    with pytest.raises(container.LaborError) as e:
        lab_project.create(admin="boss", model="gibt-es-nicht-xyz")
    assert e.value.code == "labor_model_unavailable"
