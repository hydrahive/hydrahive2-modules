"""Werkzeuge für Agenten (Spec §6): diagramm_erstellen, diagramm_hilfe."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from backend import store, tools
from conftest import PROJECT_ID


def _ctx(ws, project_id=PROJECT_ID, user="testuser"):
    from hydrahive.tools.base import ToolContext
    return ToolContext(session_id="sess1", agent_id="agent1", user_id=user, workspace=ws, project_id=project_id)


def _create(ctx, **args):
    base = {"art": "workflow", "beschreibung": json.dumps({"meta": {"title": "Websuche"}})}
    base.update(args)
    return asyncio.run(tools.diagramm_erstellen.execute(base, ctx))


def test_tools_are_registered_with_clear_names():
    assert tools.diagramm_erstellen.name == "diagramm_erstellen"
    assert tools.diagramm_hilfe.name == "diagramm_hilfe"
    assert {t.name for t in tools.TOOLS} == {"diagramm_erstellen", "diagramm_hilfe", "diagramm_liste"}
    assert "delete" not in " ".join(t.name for t in tools.TOOLS)


def test_create_saves_and_returns_module_view(fake_archify, store_dir, ws):
    res = _create(_ctx(ws))
    assert res.success and res.result_type == "module_view"
    assert res.metadata["module"] == "diagramme" and res.metadata["title"] == "Websuche"
    d = store.get(res.metadata["view_id"])
    assert d["username"] == "testuser" and d["project_id"] == PROJECT_ID
    assert d["session_id"] == "sess1" and d["agent_id"] == "agent1" and d["kind"] == "workflow"
    assert "Agent fragt" in store.html(d["id"])
    assert d["id"] in res.output and "Websuche" in res.output


def test_failure_saves_nothing_and_returns_archify_hints(fake_archify, store_dir, ws):
    fake_archify["fail"] = [{"severity": "error", "code": "schema/required", "message": "/meta must have 'output'",
                             "supportedFixes": ["add required property \"output\""]}]
    before = len(store.list_for("testuser", "user"))
    res = _create(_ctx(ws))
    assert not res.success and "schema/required" in res.error and "add required property" in res.error
    assert len(store.list_for("testuser", "user")) == before


def test_new_version_with_ersetzt(fake_archify, store_dir, ws):
    first = _create(_ctx(ws)).metadata["view_id"]
    second = _create(_ctx(ws), ersetzt=first)
    assert second.success
    assert store.get(second.metadata["view_id"])["version_of"] == first
    assert store.html(first)


def test_ersetzt_unknown_or_foreign_is_refused(fake_archify, store_dir, ws):
    foreign = store.create(username="other", project_id="other-project-diagramme", session_id="s", agent_id="a",
                           title="x", kind="workflow", html="<html/>", source="{}", source_ext="json")
    for bad in ("d_gibtsnicht", foreign["id"]):
        res = _create(_ctx(ws), ersetzt=bad)
        assert not res.success and "nicht gefunden" in res.error
    assert fake_archify["calls"] == []


def test_title_comes_from_meta_or_fallback(fake_archify, store_dir, ws):
    res = _create(_ctx(ws), beschreibung=json.dumps({"meta": {}}))
    assert res.metadata["title"] == "Diagramm"
    res = _create(_ctx(ws), beschreibung="kein json")
    assert res.success and res.metadata["title"] == "Diagramm"
    res = _create(_ctx(ws), art="explainer", beschreibung="---\ntitle: Antwort zur Websuche\n---\n# x")
    assert res.metadata["title"] == "Antwort zur Websuche"


def test_meta_output_is_forced_into_own_folder(fake_archify, store_dir, ws):
    """Der Agent kann über meta.output nicht woanders hinschreiben."""
    _create(_ctx(ws), beschreibung=json.dumps({"meta": {"title": "T", "output": "../../../etc/x.html"}}))
    written = json.loads(fake_archify["calls"][0]["input"])
    assert written["meta"]["output"] == "diagramm.html"


def test_repo_inside_project_is_passed(fake_archify, store_dir, ws):
    (ws / "repo").mkdir(exist_ok=True)
    _create(_ctx(ws), art="architecture", repo="repo")
    argv = fake_archify["calls"][0]["argv"]
    assert Path(argv[argv.index("--repo-root") + 1]) == (ws / "repo").resolve()


@pytest.mark.parametrize("repo", ["../..", "/etc", "gibtsnicht"])
def test_repo_outside_project_is_refused(fake_archify, store_dir, ws, repo):
    res = _create(_ctx(ws), repo=repo)
    assert not res.success and fake_archify["calls"] == []


def test_work_folder_is_cleaned_up(fake_archify, store_dir, ws):
    _create(_ctx(ws))
    assert not fake_archify["calls"][0]["cwd"].exists()


def test_missing_args(fake_archify, store_dir, ws):
    assert not asyncio.run(tools.diagramm_erstellen.execute({"art": "workflow"}, _ctx(ws))).success
    assert not asyncio.run(tools.diagramm_erstellen.execute({"beschreibung": "{}"}, _ctx(ws))).success
    assert fake_archify["calls"] == []


def test_help_returns_schema_and_example(ws):
    res = asyncio.run(tools.diagramm_hilfe.execute({"art": "workflow"}, _ctx(ws)))
    assert res.success
    assert '"diagram_type"' in res.output and "lanes" in res.output
    assert "Beispiel" in res.output and "Schema" in res.output


def test_help_without_art_lists_kinds(ws):
    res = asyncio.run(tools.diagramm_hilfe.execute({}, _ctx(ws)))
    assert res.success
    for kind in ("architecture", "workflow", "sequence", "erd", "timeline", "explainer"):
        assert kind in res.output


def test_help_unknown_art(ws):
    res = asyncio.run(tools.diagramm_hilfe.execute({"art": "../etc"}, _ctx(ws)))
    assert not res.success


# --- S2: diagramm_liste (Spec §12.5) -----------------------------------------------------------------

def _mk(title, project_id=PROJECT_ID, username="testuser", version_of=None):
    return store.create(username=username, project_id=project_id, session_id="s", agent_id=None, title=title,
                        kind="workflow", html="<html/>", source="{}", source_ext="json", version_of=version_of)


def test_list_tool_is_registered():
    assert tools.diagramm_liste.name == "diagramm_liste"
    assert "diagramm_liste" in {t.name for t in tools.TOOLS}


def test_list_tool_shows_newest_versions(store_dir, ws):
    a = _mk("Ablauf alt")
    b = _mk("Ablauf neu", version_of=a["id"])
    c = _mk("Datenbank")
    res = asyncio.run(tools.diagramm_liste.execute({}, _ctx(ws)))
    assert res.success
    assert b["id"] in res.output and c["id"] in res.output and a["id"] not in res.output
    assert "Ablauf neu" in res.output and "2 Fassungen" in res.output


def test_list_tool_filters(store_dir, ws):
    a = _mk("Ablauf der Websuche")
    b = _mk("Fremdes Projekt", project_id=None)
    res = asyncio.run(tools.diagramm_liste.execute({"q": "websuche"}, _ctx(ws)))
    assert a["id"] in res.output and b["id"] not in res.output
    res = asyncio.run(tools.diagramm_liste.execute({"projekt": True}, _ctx(ws)))
    assert a["id"] in res.output and b["id"] not in res.output


def test_list_tool_hides_trash_and_foreign(store_dir, ws):
    a = _mk("weg")
    store.trash(a["id"])
    f = _mk("fremd", project_id="other-project-diagramme", username="other")
    res = asyncio.run(tools.diagramm_liste.execute({}, _ctx(ws)))
    assert a["id"] not in res.output and f["id"] not in res.output


def test_list_tool_limit_30(store_dir, ws):
    made = [_mk(f"D{i:02d}") for i in range(32)]
    res = asyncio.run(tools.diagramm_liste.execute({}, _ctx(ws)))
    assert made[-1]["id"] in res.output and made[0]["id"] not in res.output and made[1]["id"] not in res.output


def test_list_tool_empty(store_dir, ws):
    res = asyncio.run(tools.diagramm_liste.execute({"q": "gibtsnichtxyz"}, _ctx(ws)))
    assert res.success and "keine" in res.output.lower()


def test_create_makes_preview(fake_archify, store_dir, ws, monkeypatch):
    from backend import preview
    calls = []
    monkeypatch.setattr(preview, "make", lambda vid: calls.append(vid) or True)
    res = _create(_ctx(ws))
    assert calls == [res.metadata["view_id"]]
