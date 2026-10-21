"""Brief-Werkzeuge des Rechts-Agenten (Plan L3 Schritt 5): legal_propose_letter, legal_check_letter, Vorlagen-Gerüst."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from backend import case_tools, casefile, cases, correspondence, letter_tools
from test_correspondence import LETTER


def _ctx(user="alice", project_id=None):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="s", agent_id="a", user_id=user, workspace=Path("/nonexistent"), project_id=project_id)


def _run(tool, args, ctx):
    return asyncio.run(tool.execute(args, ctx))


@pytest.fixture(autouse=True)
def _tools(monkeypatch):
    from backend.tools import TOOLS
    from hydrahive.tools import REGISTRY
    for t in TOOLS:
        monkeypatch.setitem(REGISTRY, t.name, t)


@pytest.fixture
def pid():
    from hydrahive.projects import config as pc
    out = cases.create_case("alice", {"title": "Mietsache Hitze", "state": "NI"}, model="claude-sonnet-4-6")
    yield out["project_id"]
    pc.delete(out["project_id"])


def test_propose_letter_leaves_correspondence_untouched(pid):
    r = _run(letter_tools.PROPOSE_LETTER, LETTER, _ctx(project_id=pid))
    assert r.success and r.output["kind"] == "letter" and "check" in r.output["payload"]
    assert correspondence.list_for(pid) == [] and len(casefile.list_proposals(pid)) == 1


def test_read_role_cannot_propose_letter(pid):
    from hydrahive.projects import config as pc
    pc.update(pid, members=[{"username": "bob", "role": "read"}])
    r = _run(letter_tools.PROPOSE_LETTER, LETTER, _ctx(user="bob", project_id=pid))
    assert not r.success and "Leserechte" in r.error
    assert casefile.list_proposals(pid) == []


def test_foreign_or_no_project_fails(pid):
    assert not _run(letter_tools.PROPOSE_LETTER, LETTER, _ctx()).success
    assert not _run(letter_tools.PROPOSE_LETTER, LETTER, _ctx(user="bob", project_id=pid)).success


def test_check_letter_stores_nothing(pid):
    r = _run(letter_tools.CHECK_LETTER, {**LETTER, "body": "binnen 14 Tagen"}, _ctx(project_id=pid))
    assert r.success
    items = {i["key"]: i for i in r.output["items"]}
    assert items["deadline_date"]["ok"] is False
    assert correspondence.list_for(pid) == [] and casefile.list_proposals(pid) == []


def test_letter_draft_from_template(pid):
    me = casefile.add_party(pid, {"role": "me", "name": "Till Muster", "address": "Musterweg 1\n30159 Hannover"})
    opp = casefile.add_party(pid, {"role": "opponent", "name": "HV Müller", "address": "Hauptstr. 1\n30159 Hannover"})
    r = _run(letter_tools.LETTER_DRAFT, {"template": "mangelanzeige", "recipient_id": opp["id"]}, _ctx(project_id=pid))
    assert r.success and r.output["sender"].startswith(me["name"]) and r.output["recipient"].startswith("HV Müller")
    assert "§ 536c BGB" in r.output["body"]
    r = _run(letter_tools.LETTER_DRAFT, {"template": "gibtsnicht"}, _ctx(project_id=pid))
    assert not r.success


def test_invalid_letter_returns_error(pid):
    r = _run(letter_tools.PROPOSE_LETTER, {**LETTER, "delivery": "taube"}, _ctx(project_id=pid))
    assert not r.success and r.error


def test_case_snapshot_tool_shows_correspondence(pid):
    correspondence.add(pid, {"direction": "out", **LETTER}, by="alice")
    r = _run(case_tools.LEGAL_CASE, {}, _ctx(project_id=pid))
    assert r.success and r.output["correspondence"][0]["subject"] == "Mangelanzeige"


def test_letter_tools_private_in_manifest():
    manifest = json.loads((Path(__file__).parent.parent / "manifest.json").read_text())
    priv = {k for k, v in manifest["sensitive_tools"].items() if v == "privat"}
    assert {"legal_propose_letter", "legal_check_letter", "legal_letter_draft"} <= priv


def test_agent_gets_letter_tools(pid):
    from hydrahive.agents import config as ac
    from hydrahive.projects import config as pc
    tools = set(ac.get(pc.get(pid)["agent_id"])["tools"])
    assert {"legal_propose_letter", "legal_check_letter", "legal_letter_draft"} <= tools
