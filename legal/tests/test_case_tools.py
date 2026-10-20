"""Fall-Werkzeuge des Rechts-Agenten (Plan L2 Schritt 5): nur für ToolContext.project_id, Rechte laut Projektrolle."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from backend import case_tools, casefile, cases

FACTS = {"title": "Mietsache Hitze", "state": "NW"}


def _ctx(user="alice", project_id=None):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=Path("/nonexistent"), project_id=project_id)


def _run(tool, args, ctx):
    return asyncio.run(tool.execute(args, ctx))


@pytest.fixture
def pid():
    from hydrahive.projects import config as pc
    out = cases.create_case("alice", FACTS, model="claude-sonnet-4-6")
    yield out["project_id"]
    pc.delete(out["project_id"])


def test_without_project_or_foreign_project_fails(pid):
    assert not _run(case_tools.LEGAL_CASE, {}, _ctx()).success
    r = _run(case_tools.LEGAL_CASE, {}, _ctx(user="bob", project_id=pid))
    assert not r.success and "Kein Zugriff" in r.error


def test_project_that_is_no_case_fails():
    from hydrahive.projects import config as pc
    other = pc.create("Kein Fall", llm_model="claude-sonnet-4-6", created_by="alice")
    try:
        assert not _run(case_tools.LEGAL_CASE, {}, _ctx(project_id=other["id"])).success
    finally:
        pc.delete(other["id"])


def test_read_case(pid):
    r = _run(case_tools.LEGAL_CASE, {}, _ctx(project_id=pid))
    assert r.success and r.output["case"]["title"] == "Mietsache Hitze"


def test_read_role_may_read_but_not_propose(pid):
    from hydrahive.projects import config as pc
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    assert _run(case_tools.LEGAL_CASE, {}, _ctx(user="bob", project_id=pid)).success
    for tool, args in ((case_tools.PROPOSE_PARTY, {"role": "lawyer", "name": "X"}),
                       (case_tools.PROPOSE_FACT, {"text": "Y"}),
                       (case_tools.NOTE, {"title": "T", "body": "B"})):
        r = _run(tool, args, _ctx(user="bob", project_id=pid))
        assert not r.success and "Leserechte" in r.error
    assert casefile.list_proposals(pid) == [] and casefile.list_notes(pid) == []


def test_proposals_leave_file_untouched(pid):
    assert _run(case_tools.PROPOSE_PARTY, {"role": "lawyer", "name": "RA Meier"}, _ctx(project_id=pid)).success
    r = _run(case_tools.PROPOSE_DEADLINE, {"label": "Klage", "event_date": "2026-11-02", "kind": "weeks",
                                           "amount": 3}, _ctx(project_id=pid))
    assert r.success and r.output["payload"]["due_date"] == "2026-11-23"
    assert _run(case_tools.PROPOSE_FACT, {"text": "Brief vom 01.10."}, _ctx(project_id=pid)).success
    assert casefile.list_parties(pid) == [] and casefile.list_deadlines(pid) == []
    assert len(casefile.list_proposals(pid)) == 3
    assert {p["author_name"] for p in casefile.list_proposals(pid)} == {"Rechts-Agent"}   # Agent "a" unbekannt


def test_invalid_proposal_returns_error_not_exception(pid):
    r = _run(case_tools.PROPOSE_DEADLINE, {"label": "x", "event_date": "gestern", "kind": "days", "amount": 1},
             _ctx(project_id=pid))
    assert not r.success and r.error


def test_deadline_calc_defaults_to_case_state_and_stores_nothing(pid):
    # Fronleichnam 2027 = Do 27.05.; NW: Feiertag → Fr 28.05.
    r = _run(case_tools.DEADLINE, {"event_date": "2027-05-26", "kind": "days", "amount": 1}, _ctx(project_id=pid))
    assert r.success and r.output["due_date"] == "2027-05-28" and r.output["steps"]
    r2 = _run(case_tools.DEADLINE, {"event_date": "2027-05-26", "kind": "days", "amount": 1, "state": "NI"},
              _ctx(project_id=pid))
    assert r2.output["due_date"] == "2027-05-27"
    assert casefile.list_deadlines(pid) == [] and casefile.list_proposals(pid) == []


def test_deadline_calc_without_case_needs_state():
    r = _run(case_tools.DEADLINE, {"event_date": "2027-05-26", "kind": "days", "amount": 1}, _ctx())
    assert not r.success
    r = _run(case_tools.DEADLINE, {"event_date": "2027-05-26", "kind": "days", "amount": 1, "state": "NW"}, _ctx())
    assert r.success and r.output["due_date"] == "2027-05-28"


def test_all_case_tools_are_sensitive_in_manifest():
    import json
    manifest = json.loads((Path(__file__).parent.parent / "manifest.json").read_text())
    names = {t.name for t in case_tools.TOOLS} - {"legal_deadline"}
    assert names <= {k for k, v in manifest.get("sensitive_tools", {}).items() if v == "privat"}
