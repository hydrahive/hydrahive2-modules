"""Hydra-Labor L2 Baustein 2: Fork beim Nutzer – vorhanden, neu, oder gleichnamiges Nicht-Fork-Repo."""
from __future__ import annotations

import asyncio

import pytest
from backend import github_repos
from fake_github import TOKEN


def run(c):
    return asyncio.run(c)


def test_ziele_fest():
    assert github_repos.TARGETS == {"core": "hydrahive/hydrahive2.0", "modules": "hydrahive/hydrahive2-modules"}


def test_fork_neu_angelegt(fake_github):
    assert run(github_repos.ensure_fork(TOKEN, "nutzer", "core")) == "nutzer/hydrahive2.0"
    posts = [c for c in fake_github.calls if c["method"] == "POST"]
    assert [c["url"] for c in posts] == ["https://api.github.com/repos/hydrahive/hydrahive2.0/forks"]
    assert posts[0]["json"] == {"default_branch_only": True}


def test_fork_schon_da(fake_github):
    fake_github.repos["nutzer/hydrahive2-modules"] = {"fork": True, "parent": "hydrahive/hydrahive2-modules"}
    assert run(github_repos.ensure_fork(TOKEN, "nutzer", "modules")) == "nutzer/hydrahive2-modules"
    assert not any(c["method"] == "POST" for c in fake_github.calls)


def test_gleichnamig_aber_kein_fork(fake_github):
    fake_github.repos["nutzer/hydrahive2.0"] = {"fork": False}
    with pytest.raises(github_repos.GitHubError) as e:
        run(github_repos.ensure_fork(TOKEN, "nutzer", "core"))
    assert e.value.code == "labor_github_name_taken"
    assert not any(c["method"] == "POST" for c in fake_github.calls)


def test_fork_von_fremdem_repo(fake_github):
    fake_github.repos["nutzer/hydrahive2.0"] = {"fork": True, "parent": "jemand/hydrahive2.0"}
    with pytest.raises(github_repos.GitHubError) as e:
        run(github_repos.ensure_fork(TOKEN, "nutzer", "core"))
    assert e.value.code == "labor_github_name_taken"


def test_fork_erscheint_erst_spaeter(fake_github, monkeypatch):
    """GitHub legt Forks im Hintergrund an – bis zu 60 s warten, dann Fehler."""
    real = fake_github.request
    gets = {"n": 0}

    async def slow(method, url, **kw):
        if method == "GET" and url.endswith("/repos/nutzer/hydrahive2.0"):
            gets["n"] += 1
            if gets["n"] < 4:
                return 404, {"message": "Not Found"}, {}
        return await real(method, url, **kw)
    monkeypatch.setattr(github_repos.github_api, "request", slow)
    assert run(github_repos.ensure_fork(TOKEN, "nutzer", "core")) == "nutzer/hydrahive2.0"
    assert gets["n"] == 4


def test_fork_erscheint_nie(fake_github, monkeypatch):
    real = fake_github.request

    async def never(method, url, **kw):
        if method == "GET" and url.endswith("/repos/nutzer/hydrahive2.0"):
            return 404, {"message": "Not Found"}, {}
        return await real(method, url, **kw)
    monkeypatch.setattr(github_repos.github_api, "request", never)
    with pytest.raises(github_repos.GitHubError) as e:
        run(github_repos.ensure_fork(TOKEN, "nutzer", "core"))
    assert e.value.code == "labor_github_fork_failed"


def test_fork_abgelehnt(fake_github):
    fake_github.fail["POST https://api.github.com/repos/hydrahive/hydrahive2.0/forks"] = (403, {"message": "x"})
    with pytest.raises(github_repos.GitHubError) as e:
        run(github_repos.ensure_fork(TOKEN, "nutzer", "core"))
    assert e.value.code == "labor_github_fork_failed"


def test_unbekanntes_ziel(fake_github):
    with pytest.raises(KeyError):
        run(github_repos.ensure_fork(TOKEN, "nutzer", "plugins"))


def test_ratenbegrenzung(fake_github):
    fake_github.rate_left = "0"
    fake_github.fail["GET https://api.github.com/repos/nutzer"] = (403, {"message": "API rate limit exceeded"})
    with pytest.raises(github_repos.GitHubError) as e:
        run(github_repos.ensure_fork(TOKEN, "nutzer", "core"))
    assert e.value.code == "labor_github_rate_limited"
