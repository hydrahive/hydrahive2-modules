"""Hydra-Labor L2 Baustein 4/5: Einreichen von vorne bis hinten (Vorprüfung → Fork → Bündel → Schieben → PR),
gespeichert, Stand aktualisieren. Container, GitHub und Schieben sind Attrappen; die Teile sind einzeln geprüft."""
from __future__ import annotations

import asyncio

import pytest
from backend import github_auth, push, submit, submit_box


def run(c):
    return asyncio.run(c)


@pytest.fixture
def ready(fake_github, db_ready, monkeypatch, tmp_path):
    from fake_github import TOKEN
    from hydrahive.credentials import _crypto
    from hydrahive.db.connection import db
    from hydrahive.settings import settings
    with db() as c:
        c.execute("INSERT OR REPLACE INTO module_hydralabor_github (id, token_enc, login, user_id, scopes, connected_at) "
                  "VALUES (1, ?, 'nutzer', 4242, 'public_repo', 'x')", (_crypto.encrypt(TOKEN, settings.data_dir),))
        c.commit()
    box = {"changes": {"files": ["core/src/hydrahive/a.py"], "lines": 12}, "diff": "+++ b/a.py\n+x = 1\n",
           "tests": {"ok": True, "summary": "5241 passed in 270.0s", "passed": 5241, "failed": 0, "failures": []},
           "calls": []}

    async def changes(target):
        box["calls"].append(("changes", target))
        return box["changes"]

    async def commit(target, title, login, uid):
        box["calls"].append(("commit", target, title, login, uid))

    async def diff(target):
        box["calls"].append(("diff", target))
        return box["diff"]

    async def tests(target, files):
        box["calls"].append(("tests", target))
        return box["tests"]

    async def bundle(target, workdir):
        box["calls"].append(("bundle", target))
        p = workdir / "labor.bundle"
        p.write_bytes(b"# v2 git bundle\n")
        return p

    async def push_bundle(bundle, *, fork, target, branch, token, workdir):
        box["calls"].append(("push", fork, target, branch, token == TOKEN))
        bundle.unlink()
    for name, fn in (("changes", changes), ("commit", commit), ("diff", diff), ("run_tests", tests), ("bundle", bundle)):
        monkeypatch.setattr(submit_box, name, fn)
    monkeypatch.setattr(push, "push_bundle", push_bundle)
    monkeypatch.setattr(submit, "_workdir", lambda: tmp_path)
    monkeypatch.setattr(submit, "_stamp", lambda: "20261030-1900")
    monkeypatch.setattr(submit, "_versions", lambda: {"hydrahive": "2.0.0", "hydralabor": "0.2.0"})
    yield box
    github_auth.disconnect()


def test_ohne_github_kein_einreichen(ready):
    github_auth.disconnect()
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "Titel", "Text", report=lambda _k: None))
    assert e.value.code == "labor_github_not_connected"


def test_einreichen_komplett(ready, fake_github):
    seen = []
    out = run(submit.submit("core", "Fehler im Chat beheben", "Weil es hakt.", report=seen.append))
    assert seen == ["check", "tests", "fork", "push", "pr"]
    names = [c[0] for c in ready["calls"]]
    assert names == ["changes", "commit", "diff", "tests", "bundle", "push"]
    assert ready["calls"][1] == ("commit", "core", "Fehler im Chat beheben", "nutzer", 4242)
    assert ready["calls"][-1] == ("push", "nutzer/hydrahive2.0", "core", "labor/fehler-im-chat-beheben-20261030-1900", True)
    pr = fake_github.pulls[0]
    assert pr["head"] == "nutzer:labor/fehler-im-chat-beheben-20261030-1900" and pr["base"] == "main"
    assert pr["title"] == "Fehler im Chat beheben" and pr["maintainer_can_modify"] is True
    for part in ("Weil es hakt.", "Hydra-Labor", "5241 passed", "hydralabor 0.2.0"):
        assert part in pr["body"]
    post = next(c for c in fake_github.calls if c["url"].endswith("/repos/hydrahive/hydrahive2.0/pulls"))
    assert post["method"] == "POST"
    assert out["number"] == 100 and out["url"].endswith("/pull/100")
    assert submit.list_submissions()[0] | {} == {**submit.list_submissions()[0], "kind": "pr", "target": "core",
                                                "number": 100, "state": "submitted"}


def test_label_wird_versucht_fehler_egal(ready, fake_github):
    fake_github.fail["POST https://api.github.com/repos/hydrahive/hydrahive2.0/issues/100/labels"] = (403, {})
    run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert any(c["url"].endswith("/issues/100/labels") for c in fake_github.calls)
    assert submit.list_submissions()[0]["number"] == 100


def test_keine_aenderungen(ready):
    ready["changes"] = {"files": [], "lines": 0}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_nothing"
    assert [c[0] for c in ready["calls"]] == ["changes"]


def test_geschuetzter_pfad(ready):
    ready["changes"] = {"files": [".github/workflows/x.yml", "core/a.py"], "lines": 3}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_protected" and e.value.detail == [".github/workflows/x.yml"]
    assert "push" not in [c[0] for c in ready["calls"]]


def test_zu_gross(ready):
    ready["changes"] = {"files": [f"f{i}.py" for i in range(51)], "lines": 10}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_too_big"


def test_geheimnis_gefunden(ready):
    ready["diff"] = "+key = 'ghp_" + "a" * 36 + "'\n"
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_secret" and e.value.detail == ["ghp_aa…"]
    assert "tests" not in [c[0] for c in ready["calls"]]


def test_tests_rot(ready):
    ready["tests"] = {"ok": False, "summary": "2 failed, 10 passed", "passed": 10, "failed": 2, "failures": ["a::b"]}
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_tests_red" and e.value.detail["failed"] == 2
    assert "bundle" not in [c[0] for c in ready["calls"]]


@pytest.mark.parametrize("target", ["plugins", "", "../x"])
def test_ziel_ungueltig(ready, target):
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit(target, "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_target_invalid"


def test_text_ungueltig(ready):
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_text_invalid"


def test_pr_scheitert(ready, fake_github):
    fake_github.fail["POST https://api.github.com/repos/hydrahive/hydrahive2.0/pulls"] = (422, {"message": "x"})
    with pytest.raises(submit.SubmitError) as e:
        run(submit.submit("core", "T", "B", report=lambda _k: None))
    assert e.value.code == "labor_submit_pr_failed"
    assert submit.list_submissions() == []


def test_ziel_vorschlagen(ready):
    ready["changes"] = {"files": ["radiostream/a.py"], "lines": 1}
    assert run(submit.suggest_target()) in ("core", "modules", "")


def test_stand_aktualisieren(ready, fake_github):
    run(submit.submit("core", "A", "B", report=lambda _k: None))
    run(submit.submit("core", "C", "D", report=lambda _k: None))
    fake_github.pulls[0].update(state="closed", merged=True)
    fake_github.pulls[1].update(state="closed", merged=False)
    run(submit.refresh())
    by_num = {s["number"]: s["state"] for s in submit.list_submissions()}
    assert by_num == {100: "merged", 101: "closed"}
    n = len(fake_github.calls)
    run(submit.refresh())                                          # abgeschlossene werden nicht mehr abgefragt
    assert len(fake_github.calls) == n


def test_token_nie_in_gespeicherten_daten(ready):
    from fake_github import TOKEN
    from hydrahive.db.connection import db
    run(submit.submit("core", "T", "B", report=lambda _k: None))
    with db() as c:
        rows = c.execute("SELECT * FROM module_hydralabor_submissions").fetchall()
    assert TOKEN not in str([tuple(r) for r in rows])
