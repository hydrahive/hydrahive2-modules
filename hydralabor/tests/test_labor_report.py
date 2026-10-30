"""Hydra-Labor L2 Baustein 6: Fehler melden → Issue mit Versionen, Geheimnisse vorher entfernt."""
from __future__ import annotations

import asyncio

import pytest
from backend import github_auth, report, submit


def run(c):
    return asyncio.run(c)


@pytest.fixture
def connected(fake_github, db_ready, monkeypatch):
    from fake_github import TOKEN
    from hydrahive.credentials import _crypto
    from hydrahive.db.connection import db
    from hydrahive.settings import settings
    with db() as c:
        c.execute("INSERT OR REPLACE INTO module_hydralabor_github (id, token_enc, login, user_id, scopes, connected_at) "
                  "VALUES (1, ?, 'nutzer', 4242, 'public_repo', 'x')", (_crypto.encrypt(TOKEN, settings.data_dir),))
        c.commit()
    monkeypatch.setattr(report, "_environment", lambda: {"hydrahive": "2.0.0", "hydralabor": "0.2.0",
                                                         "system": "Ubuntu 24.04"})
    yield fake_github
    github_auth.disconnect()


def test_issue_angelegt(connected):
    out = run(report.report("modules", "Knopf geht nicht", "Ich klicke", "Es passiert was", "1. Klick"))
    iss = connected.issues[0]
    assert iss["title"] == "Knopf geht nicht"
    for part in ("Ich klicke", "Es passiert was", "1. Klick", "hydralabor 0.2.0", "Ubuntu 24.04", "Hydra-Labor"):
        assert part in iss["body"]
    post = connected.calls[-2]
    assert post["url"] == "https://api.github.com/repos/hydrahive/hydrahive2-modules/issues"
    assert out["number"] == 500
    assert submit.list_submissions()[0]["kind"] == "issue"


def test_geheimnis_wird_entfernt(connected):
    run(report.report("core", "T", "mein key ist ghp_" + "a" * 36, "", ""))
    assert "ghp_" + "a" * 36 not in connected.issues[0]["body"]


def test_ohne_github(connected):
    github_auth.disconnect()
    with pytest.raises(submit.SubmitError) as e:
        run(report.report("core", "T", "x", "", ""))
    assert e.value.code == "labor_github_not_connected"


@pytest.mark.parametrize(("title", "what"), [("", "x"), ("a" * 121, "x"), ("T", ""), ("T", "x" * 4001)])
def test_eingaben_begrenzt(connected, title, what):
    with pytest.raises(submit.SubmitError) as e:
        run(report.report("core", title, what, "", ""))
    assert e.value.code == "labor_submit_text_invalid"


def test_issue_scheitert(connected):
    connected.fail["POST https://api.github.com/repos/hydrahive/hydrahive2.0/issues"] = (410, {"message": "Issues off"})
    with pytest.raises(submit.SubmitError) as e:
        run(report.report("core", "T", "x", "", ""))
    assert e.value.code == "labor_report_failed"
