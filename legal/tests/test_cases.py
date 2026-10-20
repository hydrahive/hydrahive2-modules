"""Fall = Projekt mit Rechts-Agent (Plan L2 Schritte 2–3). Muster wie storyteller/tests/test_team_setup.py."""
from __future__ import annotations

import pytest
from backend import access, cases

FACTS = {"title": "Mietsache Hitze", "area": "Mietrecht", "state": "NW",
         "summary": "Wohnung im Sommer dauerhaft über 26 °C, Vermieter informiert, keine Abhilfe.",
         "facts": "Seit Juni 2026 Messwerte …", "goal": "Abhilfe bzw. Mietminderung"}

FORBIDDEN = {"shell_exec", "file_read", "file_write", "file_patch", "fetch_url", "web_browser", "send_mail",
             "ask_agent", "create_specialist", "configure_specialist"}


@pytest.fixture(autouse=True)
def _module_tools_registered(monkeypatch):
    from backend.tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def created():
    from hydrahive.projects import config as pc
    made: list[str] = []
    yield made
    for pid in made:
        pc.delete(pid)


def _make(created, user="alice", **kw):
    out = cases.create_case(user, {**FACTS, **kw.pop("fields", {})}, model=kw.pop("model", "claude-sonnet-4-6"))
    created.append(out["project_id"])
    return out


def test_creates_project_case_and_legal_agent(created):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    out = _make(created)
    p = pc.get(out["project_id"])
    assert p["name"] == "Recht – Mietsache Hitze" and p["created_by"] == "alice"
    assert p["metadata"]["legal"] == {"case": True}
    assert "Mietsache Hitze" in p["description"] and "Mietrecht" in p["description"]
    case = cases.get_case(p["id"])
    assert case["title"] == "Mietsache Hitze" and case["state"] == "NW" and case["status"] == "open"
    agent = ac.get(p["agent_id"])
    assert agent["name"] == "Recht – Mietsache Hitze — Rechts-Agent"
    assert {"legal_case", "legal_search", "legal_norm", "legal_deadline", "legal_propose_deadline"} <= set(agent["tools"])
    assert "Mietsache Hitze" in ac.get_system_prompt(agent["id"])


def test_agent_has_no_outward_or_file_tools(created):
    from hydrahive.agents import config as ac
    from hydrahive.db._mirror_groups import OUTWARD_TOOLS
    from hydrahive.projects import config as pc
    agent = ac.get(pc.get(_make(created)["project_id"])["agent_id"])
    assert not set(agent["tools"]) & OUTWARD_TOOLS
    assert not set(agent["tools"]) & FORBIDDEN


def test_prompt_demands_sources_and_names_limits(created):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    prompt = ac.get_system_prompt(pc.get(_make(created)["project_id"])["agent_id"])
    for must in ("legal_norm", "Vorschlag", "Rechenweg", "Anwalt", "keine Rechtsberatung"):
        assert must.lower() in prompt.lower(), must


@pytest.mark.parametrize("bad", [{"title": ""}, {"title": "x" * 201}, {"state": "XX"}, {"area": "y" * 101}])
def test_invalid_input_creates_nothing(created, bad):
    from hydrahive.projects import config as pc
    before = {p["id"] for p in pc.list_all()}
    with pytest.raises(cases.CaseError):
        _make(created, fields=bad)
    assert {p["id"] for p in pc.list_all()} == before


def test_failure_after_project_rolls_back(created, monkeypatch):
    from hydrahive.projects import config as pc
    before = {p["id"] for p in pc.list_all()}

    def boom(*a, **k):
        raise RuntimeError("DB kaputt")
    monkeypatch.setattr(cases, "_insert_case", boom)
    with pytest.raises(RuntimeError):
        _make(created)
    assert {p["id"] for p in pc.list_all()} == before


def test_model_falls_back_to_default_and_no_model_is_refused(created, monkeypatch):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    monkeypatch.setattr(cases, "default_model", lambda: "claude-haiku-4-5")
    out = _make(created, model="")
    assert ac.get(pc.get(out["project_id"])["agent_id"])["llm_model"] == "claude-haiku-4-5"
    monkeypatch.setattr(cases, "default_model", lambda: "")
    with pytest.raises(cases.CaseError) as e:
        _make(created, model="")
    assert e.value.code == "no_model"


# ── Zugriff über die Projektrolle ─────────────────────────────────────────────

def test_access_by_project_role(created):
    from hydrahive.projects import config as pc
    pid = _make(created)["project_id"]
    assert access.case_access("alice", "user", pid, "write") == "ok"          # Ersteller
    assert access.case_access("bob", "user", pid, "read") == "missing"        # kein Mitglied
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    assert access.case_access("bob", "user", pid, "read") == "ok"
    assert access.case_access("bob", "user", pid, "write") == "read_only"
    pc.update(pid, members=[{"username": "bob", "role": "write"}])
    assert access.case_access("bob", "user", pid, "write") == "ok"
    assert access.case_access("root", "admin", pid, "write") == "ok"


def test_project_without_case_is_not_a_case(created):
    from hydrahive.projects import config as pc
    other = pc.create("Irgendein Projekt", llm_model="claude-sonnet-4-6", created_by="alice")
    created.append(other["id"])
    assert access.case_access("alice", "user", other["id"], "read") == "missing"


def test_list_only_own_and_member_cases(created):
    from hydrahive.projects import config as pc
    a = _make(created, user="alice")["project_id"]
    b = _make(created, user="bob", fields={"title": "Bobs Fall"})["project_id"]
    assert [c["project_id"] for c in cases.list_cases("alice", "user")] == [a]
    pc.update(b, members=[{"username": "alice", "role": "read"}])
    assert {c["project_id"] for c in cases.list_cases("alice", "user")} == {a, b}
    assert {c["project_id"] for c in cases.list_cases("root", "admin")} >= {a, b}


def test_update_case_fields(created):
    pid = _make(created)["project_id"]
    cases.update_case(pid, {"status": "waiting", "their_ref": "Az. 12/345"})
    c = cases.get_case(pid)
    assert c["status"] == "waiting" and c["their_ref"] == "Az. 12/345"
    with pytest.raises(cases.CaseError):
        cases.update_case(pid, {"status": "gewonnen"})
    with pytest.raises(cases.CaseError):
        cases.update_case(pid, {"project_id": "anderes"})
