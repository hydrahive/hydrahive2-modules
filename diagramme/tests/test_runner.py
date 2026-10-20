"""Archify-Aufruf (Spec §4, §5): feste Argumente, kein Shell, Zeitgrenze, kein Update-Check, nur eigener Ordner."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend import runner


def test_success_returns_html_and_calls_finalize(fake_archify, tmp_path):
    res = runner.build("workflow", '{"meta": {"title": "T"}}', work=tmp_path)
    assert res.ok and "Agent fragt" in res.html
    call = fake_archify["calls"][0]
    argv = call["argv"]
    assert argv[0].endswith("node") or argv[0] == "node"
    assert argv[1].endswith("vendor/archify/bin/archify.mjs")
    assert argv[2:5] == ["finalize", "workflow", "eingabe.json"]
    assert argv[5] == "diagramm.html"
    assert "--json" in argv and argv[argv.index("--quality") + 1] == "showcase"
    assert call["cwd"] == tmp_path
    assert call["timeout"] == runner.TIMEOUT_SECONDS == 180


def test_environment_disables_update_check_and_sets_chrome(fake_archify, tmp_path, monkeypatch):
    monkeypatch.setattr(runner.chrome, "find", lambda: "/opt/chrome/chrome")
    runner.build("workflow", "{}", work=tmp_path)
    env = fake_archify["calls"][0]["env"]
    assert env["ARCHIFY_UPDATE_CHECK_DISABLED"] == "1"
    assert env["ARCHIFY_CHROME"] == "/opt/chrome/chrome"
    assert env["ARCHIFY_CHROME_NO_SANDBOX"] == "1"
    assert "HH_SECRET_KEY" not in env and "GH_TOKEN" not in env


def test_without_chrome_no_chrome_var(fake_archify, tmp_path, monkeypatch):
    monkeypatch.setattr(runner.chrome, "find", lambda: None)
    runner.build("workflow", "{}", work=tmp_path)
    assert "ARCHIFY_CHROME" not in fake_archify["calls"][0]["env"]


def test_input_written_as_file(fake_archify, tmp_path):
    runner.build("workflow", '{"x": 1}', work=tmp_path)
    assert (tmp_path / "eingabe.json").read_text() == '{"x": 1}'


def test_explainer_uses_markdown_input(fake_archify, tmp_path):
    runner.build("explainer", "# Antwort", work=tmp_path)
    argv = fake_archify["calls"][0]["argv"]
    assert argv[2:5] == ["finalize", "explainer", "candidate.archify.md"]
    assert (tmp_path / "candidate.archify.md").read_text() == "# Antwort"


@pytest.mark.parametrize("kind", ["evil", "", "workflow;rm", "../x", "Workflow"])
def test_unknown_kind_is_refused_without_running(fake_archify, tmp_path, kind):
    res = runner.build(kind, "{}", work=tmp_path)
    assert not res.ok and res.code == "diagram_kind_unknown"
    assert fake_archify["calls"] == []


def test_too_large_input_is_refused(fake_archify, tmp_path):
    res = runner.build("workflow", "x" * (runner.MAX_INPUT_BYTES + 1), work=tmp_path)
    assert not res.ok and res.code == "diagram_input_too_large"
    assert fake_archify["calls"] == []


def test_exactly_max_input_is_fine(fake_archify, tmp_path):
    assert runner.build("workflow", "x" * runner.MAX_INPUT_BYTES, work=tmp_path).ok


def test_archify_errors_are_short_and_without_paths(fake_archify, tmp_path):
    fake_archify["fail"] = [
        {"severity": "error", "code": "schema/required", "message": f"/meta must have 'title' at {tmp_path}/eingabe.json",
         "supportedFixes": ["add required property \"title\""]},
    ] + [{"severity": "error", "code": f"x/{i}", "message": "m" * 500} for i in range(30)]
    res = runner.build("workflow", "{}", work=tmp_path)
    assert not res.ok and res.code == "diagram_invalid"
    assert "schema/required" in res.detail and "add required property" in res.detail
    assert str(tmp_path) not in res.detail
    assert len(res.detail) <= runner.MAX_DETAIL_CHARS
    assert res.html is None


def test_timeout_is_reported(monkeypatch, tmp_path):
    def slow(argv, *, cwd, env, timeout):
        raise runner.subprocess.TimeoutExpired(argv, timeout)
    monkeypatch.setattr(runner, "_run_process", slow)
    res = runner.build("workflow", "{}", work=tmp_path)
    assert not res.ok and res.code == "diagram_timeout"


def test_missing_node_is_reported(monkeypatch, tmp_path):
    def gone(argv, *, cwd, env, timeout):
        raise FileNotFoundError("node")
    monkeypatch.setattr(runner, "_run_process", gone)
    res = runner.build("workflow", "{}", work=tmp_path)
    assert not res.ok and res.code == "diagram_node_missing"


def test_ok_but_no_html_is_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "_run_process", lambda argv, **k: (0, json.dumps({"ok": True})))
    res = runner.build("workflow", "{}", work=tmp_path)
    assert not res.ok and res.code == "diagram_failed"


def test_repo_root_is_passed_when_given(fake_archify, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    work = tmp_path / "w"
    work.mkdir()
    runner.build("architecture", "{}", work=work, repo_root=repo)
    argv = fake_archify["calls"][0]["argv"]
    assert argv[argv.index("--repo-root") + 1] == str(repo)


def test_real_process_runner_uses_no_shell(monkeypatch, tmp_path):
    seen = {}

    def fake_run(argv, **kw):
        seen.update(kw, argv=argv)
        return runner.subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    code, out = runner._run_process(["node", "x"], cwd=tmp_path, env={"A": "1"}, timeout=5)
    assert code == 0 and out == "{}"
    assert seen.get("shell", False) is False and seen["timeout"] == 5 and seen["cwd"] == tmp_path
    assert seen["env"] == {"A": "1"} and isinstance(seen["argv"], list)
    assert seen["stdin"] == runner.subprocess.DEVNULL


def test_vendor_copy_is_complete():
    vendor = Path(runner.ARCHIFY_BIN).parents[1]
    assert (vendor / "LICENSE").is_file() and (vendor / "SKILL.md").is_file()
    assert not list(vendor.glob("examples/**/*.html")), "keine fertig gebauten Beispielseiten"
    text = (vendor.parent / "VENDOR.md").read_text()
    assert "3.2.0" in text and "208acba8d412335185b2056fedf54b3405df43fb" in text
