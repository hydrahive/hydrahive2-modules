"""T1e: Helfer einer Rolle im Buch-Projekt finden (gemeinsam für Nachziehen und Team-Knöpfe)."""
from __future__ import annotations

import pytest
from backend import team
from backend.team import setup
from conftest import OTHER_PROJECT_ID


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from backend.agent_tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def book_project():
    from hydrahive.projects import config as pc
    out = setup.create_book_project("testuser", {"title": "Der Leuchtturm", "kind": "novel", "language": "de"},
                                    model="claude-sonnet-4-6")
    yield pc.get(out["project_id"])
    pc.delete(out["project_id"])


def test_finds_each_helper_by_role(book_project):
    for role in team.HELPERS:
        agent = team.helper_for(book_project, role.key)
        assert agent is not None and agent["name"].endswith(f"— {role.name}")
        assert agent["id"] in book_project["allowed_specialists"]


def test_unknown_role_and_author_are_none(book_project):
    assert team.helper_for(book_project, "author") is None
    assert team.helper_for(book_project, "hacker") is None


def test_agent_of_other_project_with_matching_name_is_ignored(book_project):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    alien = ac.create(agent_type="specialist", name="Fremd — Plausibilität", llm_model="m", tools=[], owner="other",
                      temperature=0.7, max_tokens=1000, thinking_budget=0, project_id=OTHER_PROJECT_ID)
    try:
        own = team.helper_for(book_project, "plausibility")
        pc.update(book_project["id"], allowed_specialists=[alien["id"]])
        assert team.helper_for(pc.get(book_project["id"]), "plausibility") is None
        assert own is not None
    finally:
        pc.update(book_project["id"], allowed_specialists=book_project["allowed_specialists"])
        ac.delete(alien["id"])


def test_role_of_needs_membership_in_allowed_specialists(book_project):
    from hydrahive.agents import config as ac
    plaus = team.helper_for(book_project, "plausibility")
    assert team.role_of(book_project, plaus).key == "plausibility"
    stranger = {**book_project, "allowed_specialists": []}
    assert team.role_of(stranger, ac.get(plaus["id"])) is None


def test_removed_helper_is_none(book_project):
    from hydrahive.projects import config as pc
    plaus = team.helper_for(book_project, "plausibility")
    pc.update(book_project["id"], allowed_specialists=[i for i in book_project["allowed_specialists"]
                                                       if i != plaus["id"]])
    assert team.helper_for(pc.get(book_project["id"]), "plausibility") is None
