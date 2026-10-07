"""T1c: „Neues Buch“ → eigenes Projekt mit Autor + 7 Helfern (Spec schreib-team.md §4, Plan schreib-team-t1c.md)."""
from __future__ import annotations

import pytest

from backend import storage, team
from backend.team import setup

FIELDS = {"title": "Der Leuchtturm", "kind": "novel", "language": "de", "audience": "", "idea": "Ein Sommer am Meer."}


@pytest.fixture(autouse=True)
def _module_tools_registered(monkeypatch):
    """Wie im Betrieb: der Kern hat die Storyteller-Werkzeuge registriert (loader → register_tool)."""
    from hydrahive.tools import REGISTRY

    from backend.agent_tools import TOOLS
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def created():
    from hydrahive.projects import config as pc
    made: list[str] = []
    yield made
    for pid in made:
        pc.delete(pid)


def _make(created, **kw):
    out = setup.create_book_project("testuser", {**FIELDS, **kw.pop("fields", {})}, **kw)
    created.append(out["project_id"])
    return out


def test_creates_project_book_author_and_seven_helpers(created):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    out = _make(created, model="claude-sonnet-4-6")
    p = pc.get(out["project_id"])
    assert p["name"] == "Der Leuchtturm" and p["created_by"] == "testuser"
    assert p["metadata"]["storyteller"] == {"book_id": out["book"]["id"], "team_version": team.TEAM_VERSION}
    assert storage.get_book(p["id"], out["book"]["id"])["title"] == "Der Leuchtturm"
    assert storage.get_book(p["id"], out["book"]["id"])["model"] == "claude-sonnet-4-6"

    author = ac.get(p["agent_id"])
    assert author["name"] == "Der Leuchtturm — Autor" and author["llm_model"] == "claude-sonnet-4-6"
    assert set(author["tools"]) <= set(team.AUTHOR.tools) and "shell_exec" not in author["tools"]
    assert {"storyteller_propose_text", "ask_agent"} <= set(author["tools"])
    prompt = ac.get_system_prompt(author["id"])
    assert "Autor des Buchs „Der Leuchtturm“" in prompt

    helpers = [ac.get(i) for i in p["allowed_specialists"]]
    assert [h["name"] for h in helpers] == [f"Der Leuchtturm — {r.name}" for r in team.HELPERS]
    for h, role in zip(helpers, team.HELPERS):
        assert h["type"] == "specialist" and h["project_id"] == p["id"] and h["owner"] == "testuser"
        assert h["llm_model"] == "claude-sonnet-4-6"
        assert set(h["tools"]) <= set(role.tools) and "shell_exec" not in h["tools"]
        assert ac.get_system_prompt(h["id"]).startswith("# Du ")
    assert out["team"]["author"] == author["id"] and len(out["team"]["helpers"]) == 7
    for h in helpers:                                   # Autor kennt die IDs seines Teams
        assert h["id"] in prompt


def test_model_falls_back_to_hydrahive_default(created, monkeypatch):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    monkeypatch.setattr(setup, "default_model", lambda: "claude-haiku-4-5")
    out = _make(created, model="")
    p = pc.get(out["project_id"])
    assert ac.get(p["agent_id"])["llm_model"] == "claude-haiku-4-5"
    assert {ac.get(i)["llm_model"] for i in p["allowed_specialists"]} == {"claude-haiku-4-5"}


def test_no_model_at_all_is_refused_and_nothing_created(created, monkeypatch, setup_test_env):
    from backend._files import StoryError
    monkeypatch.setattr(setup, "default_model", lambda: "")
    before = _inventory(setup_test_env)
    with pytest.raises(StoryError) as exc:
        setup.create_book_project("testuser", FIELDS, model="")
    assert exc.value.code == "no_model" and _inventory(setup_test_env) == before


def test_invalid_book_fields_create_nothing(setup_test_env):
    from backend._files import StoryError
    before = _inventory(setup_test_env)
    with pytest.raises(StoryError):
        setup.create_book_project("testuser", {**FIELDS, "kind": "gedicht"}, model="claude-sonnet-4-6")
    with pytest.raises(StoryError):
        setup.create_book_project("testuser", {**FIELDS, "title": "  "}, model="claude-sonnet-4-6")
    assert _inventory(setup_test_env) == before


def test_failure_midway_removes_everything(monkeypatch, setup_test_env):
    from hydrahive.agents import config as ac
    before = _inventory(setup_test_env)
    real, calls = ac.create, []

    def flaky(*a, **kw):
        calls.append(kw.get("name"))
        if len(calls) == 3:
            raise RuntimeError("Platte voll")
        return real(*a, **kw)
    monkeypatch.setattr(ac, "create", flaky)
    with pytest.raises(RuntimeError):
        setup.create_book_project("testuser", FIELDS, model="claude-sonnet-4-6")
    assert len(calls) == 3 and _inventory(setup_test_env) == before


def _inventory(root):
    """Projekte, Agenten, Workspaces – zum Vergleich vorher/nachher."""
    data = root / "data"
    return tuple(sorted(str(p.relative_to(data)) for sub in ("projects", "agents", "workspaces/projects")
                        for p in (data / sub).glob("*") if (data / sub).is_dir()))
