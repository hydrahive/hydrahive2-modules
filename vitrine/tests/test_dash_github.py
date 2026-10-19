"""S2 „Wartet auf Till“: offene PRs + CI, nur GET, Token nie im Ergebnis/Log (SPEC-STATUSZENTRALE.md, S2/GitHub)."""
from __future__ import annotations

import logging

import pytest

from backend import dash_github as gh

TOKEN = "ghp_" + "A" * 36
PROJECT = {"id": "p1", "name": "Hydrahive DEV", "git_token": "",
           "git_repos": {"hydrahive2": {"git_token": TOKEN}, "x": {"git_token": "anderer"}}}


class Fake:
    def __init__(self, routes=None, exc=None):
        self.calls, self.routes, self.exc = [], routes or {}, exc

    def __call__(self, method, url, headers, timeout):
        self.calls.append((method, url, dict(headers), timeout))
        if self.exc:
            raise self.exc
        for key, val in self.routes.items():
            if key in url:
                return val
        return (404, {})


PRS = [{"number": 7, "title": "feat: tolles Ding", "head": {"sha": "abc123"}, "draft": False, "html_url": "u"},
       {"number": 8, "title": "wip", "head": {"sha": "def456"}, "draft": True, "html_url": "u"}]


def _routes(runs7, runs8=None, m7=True, m8=None):
    return {"/pulls?": (200, PRS), "/commits/abc123/check-runs": (200, {"check_runs": runs7}),
            "/commits/def456/check-runs": (200, {"check_runs": runs8 or []}),
            "/pulls/7": (200, {"mergeable": m7}), "/pulls/8": (200, {"mergeable": m8})}


def test_token_aus_projekt_wie_im_kern():
    assert gh.token_of(PROJECT) == TOKEN
    assert gh.token_of({"git_token": "root", "git_repos": {}}) == "root"
    assert gh.token_of({"git_repos": {}}) is None


def test_projekt_per_name_oder_id():
    projects = [{"id": "a", "name": "Anders"}, PROJECT]
    assert gh.find_project("Hydrahive DEV", projects) is PROJECT
    assert gh.find_project("p1", projects) is PROJECT
    assert gh.find_project("gibtsnicht", projects) is None


def test_prs_mit_ci_status():
    f = Fake(_routes([{"status": "completed", "conclusion": "success"}],
                     [{"status": "in_progress", "conclusion": None}]))
    r = gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=f)
    assert r["error"] is None
    assert [(p["number"], p["ci"], p["draft"]) for p in r["prs"]] == [(7, "green", False), (8, "running", True)]
    assert r["prs"][0]["repo"] == "hydrahive2"
    assert [p["mergeable"] for p in r["prs"]] == [True, None], "None = GitHub rechnet noch"


def test_mergebar_false_bei_konflikt():
    r = gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=Fake(_routes([], m7=False)))
    assert r["prs"][0]["mergeable"] is False


@pytest.mark.parametrize("runs,expect", [
    ([], "none"),
    ([{"status": "completed", "conclusion": "failure"}, {"status": "completed", "conclusion": "success"}], "red"),
    ([{"status": "completed", "conclusion": "skipped"}, {"status": "completed", "conclusion": "success"}], "green"),
    ([{"status": "queued", "conclusion": None}], "running"),
])
def test_ci_zusammenfassung(runs, expect):
    assert gh.ci_state(runs) == expect


def test_nur_get_feste_urls_token_nur_im_header(caplog):
    caplog.set_level(logging.DEBUG)
    f = Fake(_routes([]))
    r = gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=f)
    assert {c[0] for c in f.calls} == {"GET"}
    assert all(c[1].startswith("https://api.github.com/repos/hydrahive/hydrahive2/") for c in f.calls)
    assert all(c[2]["Authorization"] == f"Bearer {TOKEN}" and TOKEN not in c[1] for c in f.calls)
    assert all(c[3] <= 10 for c in f.calls)
    assert TOKEN not in repr(r) and TOKEN not in caplog.text


@pytest.mark.parametrize("bad", ["hydrahive", "a/b/c", "../x/y", "../x", "a/..", "a/.", "a b/c", "a/b?x=1", "https://evil/x", ""])
def test_falsches_repo_format_abgelehnt(bad):
    f = Fake(_routes([]))
    r = gh.open_prs([bad], TOKEN, fetch=f)
    assert f.calls == [] and r["prs"] == []


def test_fehler_und_timeout_werden_text_ohne_token(caplog):
    caplog.set_level(logging.DEBUG)
    r = gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=Fake(exc=TimeoutError(f"timeout {TOKEN}")))
    assert r["prs"] == [] and r["error"] == "GitHub nicht erreichbar"
    assert TOKEN not in caplog.text
    r = gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=Fake({"/pulls?": (401, {"message": "Bad credentials"})}))
    assert r["error"] == "GitHub nicht erreichbar"


def test_ohne_token_kein_aufruf():
    f = Fake(_routes([]))
    r = gh.open_prs(["hydrahive/hydrahive2"], None, fetch=f)
    assert f.calls == [] and r["error"] == "Kein GitHub-Zugang"


def test_titel_gekuerzt_und_hoechstens_zehn():
    many = [{"number": i, "title": "t" * 300, "head": {"sha": f"{i:040x}"}, "draft": False} for i in range(30)]
    r = gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=Fake({"/pulls?": (200, many)}))
    assert len(r["prs"]) == gh.MAX_PRS and all(len(p["title"]) <= gh.TITLE_MAX for p in r["prs"])


def test_echter_abrufer_folgt_keiner_weiterleitung():
    import urllib.request
    opener = gh._opener()
    assert any(isinstance(h, gh._NoRedirect) for h in opener.handlers)
    assert not any(type(h) is urllib.request.HTTPRedirectHandler for h in opener.handlers)


@pytest.fixture(autouse=True)
def _leer():
    gh.reset_cache()
    yield
    gh.reset_cache()


def test_fertige_prs_werden_nicht_erneut_abgefragt():
    """Gleicher Token wie die Agenten (5000/h): pro Commit nur einmal Details holen, solange CI fertig + mergebar bekannt."""
    f = Fake(_routes([{"status": "completed", "conclusion": "success"}], [{"status": "queued", "conclusion": None}]))
    gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=f)
    n = len(f.calls)
    gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=f)
    second = [c[1] for c in f.calls[n:]]
    assert any("/pulls?" in u for u in second), "Liste wird immer geholt"
    assert not any("abc123" in u or u.endswith("/pulls/7") for u in second), "PR 7 fertig → aus Zwischenspeicher"
    assert any("def456" in u for u in second), "PR 8 läuft noch → erneut"


def test_zwischenspeicher_begrenzt():
    for i in range(250):
        gh._done[("r", i, "a" * 40)] = ("green", True)
    gh.open_prs(["hydrahive/hydrahive2"], TOKEN, fetch=Fake(_routes([{"status": "completed", "conclusion": "success"}])))
    assert len(gh._done) <= 201
