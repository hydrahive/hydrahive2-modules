"""T1d: Teams aus 0.11.0 (Team-Version 1) beim Öffnen des Buchs auf die aktuelle Version ziehen."""
from __future__ import annotations

import pytest

from backend import team
from backend.team import setup, upgrade

FIELDS = {"title": "Der Leuchtturm", "kind": "novel", "language": "de", "audience": "", "idea": ""}


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from hydrahive.tools import REGISTRY

    from backend.agent_tools import TOOLS
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def old_team():
    """Buch-Projekt wie von 0.11.0: Team-Version 1, Werkzeuge ohne Hinweise, alte Anweisung."""
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    out = setup.create_book_project("testuser", FIELDS, model="claude-sonnet-4-6")
    p = pc.get(out["project_id"])
    for aid in [p["agent_id"], *p["allowed_specialists"]]:
        a = ac.get(aid)
        ac.update(aid, tools=[t for t in a["tools"] if t not in ("storyteller_note", "storyteller_notes")])
        ac.set_system_prompt(aid, "# alte Anweisung")
    pc.update(p["id"], metadata={**p["metadata"], "storyteller": {**p["metadata"]["storyteller"], "team_version": 1}})
    yield pc.get(p["id"])
    pc.delete(p["id"])


def test_old_team_gets_note_tools_prompts_and_version(old_team):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    assert upgrade.ensure_current(old_team["id"]) is True
    p = pc.get(old_team["id"])
    assert p["metadata"]["storyteller"]["team_version"] == team.TEAM_VERSION
    author = ac.get(p["agent_id"])
    assert {"storyteller_note", "storyteller_notes", "ask_agent"} <= set(author["tools"])
    assert "storyteller_notes" in ac.get_system_prompt(author["id"]) and "Der Leuchtturm" in ac.get_system_prompt(author["id"])
    for hid, role in zip(p["allowed_specialists"], team.HELPERS):
        h = ac.get(hid)
        assert "storyteller_note" in h["tools"] and "shell_exec" not in h["tools"], role.key
        assert ac.get_system_prompt(hid).startswith("# Du ")


def test_second_call_changes_nothing(old_team, monkeypatch):
    from hydrahive.agents import config as ac
    assert upgrade.ensure_current(old_team["id"]) is True
    monkeypatch.setattr(ac, "update", lambda *a, **k: pytest.fail("darf nichts mehr ändern"))
    assert upgrade.ensure_current(old_team["id"]) is False


def test_agent_from_other_project_with_matching_name_is_untouched(old_team):
    """Steht ein fremder Agent (anderes Projekt) in allowed_specialists und heißt wie eine Rolle → nicht anfassen."""
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    from conftest import OTHER_PROJECT_ID
    alien = ac.create(agent_type="specialist", name="Der Leuchtturm — Lektor", llm_model="claude-sonnet-4-6",
                      tools=["shell_exec"], owner="other", temperature=0.7, max_tokens=1000, thinking_budget=0,
                      project_id=OTHER_PROJECT_ID)
    try:
        pc.update(old_team["id"], allowed_specialists=[*old_team["allowed_specialists"], alien["id"]])
        upgrade.ensure_current(old_team["id"])
        assert ac.get(alien["id"])["tools"] == ["shell_exec"]
    finally:
        ac.delete(alien["id"])


def test_foreign_agents_and_normal_projects_untouched(old_team):
    from hydrahive.agents import config as ac
    stranger = ac.create(agent_type="specialist", name="Fremder", llm_model="claude-sonnet-4-6", tools=["shell_exec"],
                         owner="testuser", temperature=0.7, max_tokens=1000, thinking_budget=0, project_id=old_team["id"])
    try:
        upgrade.ensure_current(old_team["id"])
        assert ac.get(stranger["id"])["tools"] == ["shell_exec"]
    finally:
        ac.delete(stranger["id"])
    from conftest import PROJECT_ID
    assert upgrade.ensure_current(PROJECT_ID) is False            # Projekt ohne metadata.storyteller
    assert upgrade.ensure_current("f" * 36) is False               # unbekanntes Projekt


def test_open_book_triggers_upgrade(client, admin_headers, old_team):
    from conftest import MOD_PREFIX
    from hydrahive.projects import config as pc
    bid = old_team["metadata"]["storyteller"]["book_id"]
    r = client.get(f"{MOD_PREFIX}/projects/{old_team['id']}/books/{bid}", headers=admin_headers)
    assert r.status_code == 200 and r.json()["open_notes"] == {}
    assert pc.get(old_team["id"])["metadata"]["storyteller"]["team_version"] == team.TEAM_VERSION


def test_upgrade_error_does_not_block_opening(client, admin_headers, old_team, monkeypatch):
    from conftest import MOD_PREFIX
    monkeypatch.setattr(upgrade, "_apply", lambda *a: (_ for _ in ()).throw(RuntimeError("kaputt")))
    bid = old_team["metadata"]["storyteller"]["book_id"]
    assert client.get(f"{MOD_PREFIX}/projects/{old_team['id']}/books/{bid}", headers=admin_headers).status_code == 200
