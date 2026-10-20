"""S2 Für alle Agenten freischalten (Spec §12.4): mit Sicherung, Zurücknehmen nur für die selbst ergänzten."""
from __future__ import annotations

import json

import pytest
from backend import agents_access
from conftest import MOD_PREFIX

TOOLS = ["diagramm_erstellen", "diagramm_hilfe", "diagramm_liste"]


@pytest.fixture
def agents(setup_test_env, store_dir, monkeypatch):
    """Drei Test-Agenten: Projekt ohne Werkzeug, Spezialist ohne, Master mit (wie default_agent_tools)."""
    from hydrahive.agents import config as agent_config
    monkeypatch.setattr(agents_access, "_known_tools", lambda: set(TOOLS))
    made = []

    def mk(kind, name, tools):
        a = agent_config.create(agent_type=kind, name=name, llm_model="claude-sonnet-4-6", owner="testuser",
                                created_by="testuser", tools=tools, temperature=0.7, max_tokens=4096,
                                thinking_budget=0)
        made.append(a["id"])
        return a["id"]

    ids = {"project": mk("project", "P", ["file_read"]),
           "specialist": mk("specialist", "S", ["fetch_url"]),
           "master": mk("master", "M", ["file_read", "diagramm_erstellen", "diagramm_hilfe"])}
    yield ids
    for aid in made:
        agent_config.delete(aid)


def _tools(aid):
    from hydrahive.agents import config as agent_config
    return agent_config.get(aid)["tools"]


def _mine(ids):
    """Nur die Test-Agenten – auf einem echten Rechner können weitere existieren (die Suite ist isoliert)."""
    return set(ids.values())


def test_status_counts(agents):
    st = agents_access.status(only=_mine(agents))
    assert st == {"total": 3, "with_tool": 1, "unlocked_by_us": 0}


def test_unlock_adds_tools_and_remembers_only_new(agents, store_dir):
    res = agents_access.unlock(only=_mine(agents))
    assert res == {"changed": 2, "errors": 0}
    for key in ("project", "specialist"):
        assert all(t in _tools(agents[key]) for t in TOOLS)
    assert _tools(agents["project"])[0] == "file_read"            # bestehende bleiben, Reihenfolge vorn
    saved = json.loads((store_dir / "_freischaltung.json").read_text())
    assert set(saved["agents"]) == {agents["project"], agents["specialist"]}
    assert agents_access.status(only=_mine(agents))["with_tool"] == 3


def test_unlock_twice_changes_nothing_more(agents):
    agents_access.unlock(only=_mine(agents))
    assert agents_access.unlock(only=_mine(agents)) == {"changed": 0, "errors": 0}


def test_relock_removes_only_from_unlocked_agents(agents, store_dir):
    agents_access.unlock(only=_mine(agents))
    res = agents_access.relock()
    assert res == {"changed": 2, "errors": 0}
    assert _tools(agents["project"]) == ["file_read"]
    assert _tools(agents["specialist"]) == ["fetch_url"]
    assert "diagramm_erstellen" in _tools(agents["master"])       # Master hatte es schon vorher
    assert json.loads((store_dir / "_freischaltung.json").read_text())["agents"] == []


def test_relock_keeps_other_tools_added_meanwhile(agents):
    from hydrahive.agents import config as agent_config
    agents_access.unlock(only=_mine(agents))
    agent_config.update(agents["project"], tools=[*_tools(agents["project"]), "web_search"])
    agents_access.relock()
    assert _tools(agents["project"]) == ["file_read", "web_search"]


def test_disabled_agent_is_skipped(agents):
    from hydrahive.agents import config as agent_config
    agent_config.update(agents["specialist"], status="disabled")
    assert agents_access.unlock(only=_mine(agents)) == {"changed": 1, "errors": 0}
    assert "diagramm_erstellen" not in _tools(agents["specialist"])


def test_error_on_one_agent_is_counted_not_fatal(agents, monkeypatch):
    from hydrahive.agents import config as agent_config
    real = agent_config.update

    def flaky(aid, **kw):
        if aid == agents["project"]:
            raise OSError("Platte voll")
        return real(aid, **kw)
    monkeypatch.setattr(agents_access.agent_config, "update", flaky)
    assert agents_access.unlock(only=_mine(agents)) == {"changed": 1, "errors": 1}


def test_relock_skips_deleted_agent(agents):
    from hydrahive.agents import config as agent_config
    agents_access.unlock(only=_mine(agents))
    agent_config.delete(agents["specialist"])
    assert agents_access.relock() == {"changed": 1, "errors": 0}


def test_routes_are_admin_only(client, auth_headers, admin_headers, agents, monkeypatch):
    monkeypatch.setattr(agents_access, "_scope", lambda: _mine(agents))
    assert client.get(f"{MOD_PREFIX}/agents-access", headers=auth_headers).status_code == 403
    assert client.post(f"{MOD_PREFIX}/agents-access", json={"on": True}, headers=auth_headers).status_code == 403
    r = client.post(f"{MOD_PREFIX}/agents-access", json={"on": True}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["changed"] == 2
    assert client.get(f"{MOD_PREFIX}/agents-access", headers=admin_headers).json()["with_tool"] == 3
    r = client.post(f"{MOD_PREFIX}/agents-access", json={"on": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["changed"] == 2
    assert client.post(f"{MOD_PREFIX}/agents-access", json={"on": "ja"}, headers=admin_headers).status_code == 422
