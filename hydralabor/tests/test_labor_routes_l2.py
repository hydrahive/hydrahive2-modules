"""Hydra-Labor L2: Schnittstellen GitHub verbinden, Einreichen (Auftrag), Fehler melden, Einreichungen – nur Admins."""
from __future__ import annotations

import time

import pytest
from backend import github_auth, jobs, state, submit

B = "/api/modules/hydralabor"


@pytest.fixture
def clean(db_ready):
    state.clear()
    github_auth.disconnect()
    yield
    state.clear()
    github_auth.disconnect()


def wait_idle():
    for _ in range(200):
        if not state.get()["running"]:
            return
        time.sleep(0.02)


@pytest.mark.parametrize(("method", "path"), [("get", "/github"), ("post", "/github/connect"),
                                              ("post", "/github/disconnect"), ("post", "/submit"),
                                              ("post", "/report"), ("get", "/submissions"),
                                              ("post", "/submissions/refresh"), ("get", "/submit/target")])
def test_nur_admins(client, user_headers, clean, method, path):
    kw = {"json": {}} if method == "post" else {}
    assert getattr(client, method)(B + path, headers=user_headers, **kw).status_code == 403


def test_github_stand_ohne_token(client, admin_headers, clean):
    r = client.get(B + "/github", headers=admin_headers)
    assert r.json() == {"connected": False, "login": "", "pending": False, "configured": True}


def test_verbinden_gibt_code_und_wartet_im_hintergrund(client, admin_headers, clean, monkeypatch):
    calls = []

    async def fake_start():
        calls.append("start")
        return {"user_code": "ABCD-1234", "verification_uri": "https://github.com/login/device", "expires_in": 900}

    async def fake_wait():
        calls.append("wait")
        return {"connected": True, "login": "nutzer"}
    monkeypatch.setattr(github_auth, "start", fake_start)
    monkeypatch.setattr(github_auth, "wait", fake_wait)
    r = client.post(B + "/github/connect", headers=admin_headers, json={})
    assert r.status_code == 200 and r.json()["user_code"] == "ABCD-1234"
    for _ in range(100):
        if "wait" in calls:
            break
        time.sleep(0.02)
    assert calls == ["start", "wait"]


def test_verbinden_fehler_als_code(client, admin_headers, clean, monkeypatch):
    async def boom():
        raise github_auth.GitHubError("labor_github_not_configured")
    monkeypatch.setattr(github_auth, "start", boom)
    r = client.post(B + "/github/connect", headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_github_not_configured"


def test_trennen(client, admin_headers, clean):
    assert client.post(B + "/github/disconnect", headers=admin_headers, json={}).status_code == 200


def test_einreichen_als_auftrag(client, admin_headers, clean, monkeypatch):
    got = {}

    async def fake_submit(target, title, body, *, report):
        got.update(target=target, title=title, body=body)
        report("pr")
        return {"number": 7, "url": "https://github.com/hydrahive/hydrahive2.0/pull/7"}
    monkeypatch.setattr(submit, "submit", fake_submit)
    state.set_step("ready")
    r = client.post(B + "/submit", headers=admin_headers, json={"target": "core", "title": "T", "body": "B"})
    assert r.status_code == 202
    wait_idle()
    assert got == {"target": "core", "title": "T", "body": "B"}
    s = client.get(B + "/state", headers=admin_headers).json()
    assert s["submit_out"] == {"number": 7, "url": "https://github.com/hydrahive/hydrahive2.0/pull/7"}
    assert s["error_code"] == ""


def test_einreichen_fehler_mit_details(client, admin_headers, clean, monkeypatch):
    async def red(target, title, body, *, report):
        raise submit.SubmitError("labor_submit_protected", [".github/x.yml"])
    monkeypatch.setattr(submit, "submit", red)
    state.set_step("ready")
    client.post(B + "/submit", headers=admin_headers, json={"target": "core", "title": "T", "body": "B"})
    wait_idle()
    s = client.get(B + "/state", headers=admin_headers).json()
    assert s["error_code"] == "labor_submit_protected" and s["submit_out"] == {"detail": [".github/x.yml"]}


@pytest.mark.parametrize("body", [{"target": "plugins", "title": "T", "body": ""}, {"target": "core", "title": ""},
                                  {"target": "core", "title": "x" * 121}, {"target": "core", "title": "T", "x": 1}])
def test_einreichen_ungueltig(client, admin_headers, clean, body):
    state.set_step("ready")
    assert client.post(B + "/submit", headers=admin_headers, json=body).status_code in (400, 422)
    assert state.get()["running"] == ""


def test_einreichen_nur_wenn_fertig(client, admin_headers, clean):
    r = client.post(B + "/submit", headers=admin_headers, json={"target": "core", "title": "T", "body": ""})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_not_ready"


def test_ziel_vorschlag(client, admin_headers, clean, monkeypatch):
    async def guess():
        return "modules"
    monkeypatch.setattr(submit, "suggest_target", guess)
    state.set_step("ready")
    assert client.get(B + "/submit/target", headers=admin_headers).json() == {"target": "modules"}


def test_fehler_melden(client, admin_headers, clean, monkeypatch):
    from backend import report
    got = {}

    async def fake(target, title, what, expected, steps):
        got.update(target=target, title=title, what=what)
        return {"number": 3, "url": "u"}
    monkeypatch.setattr(report, "report", fake)
    r = client.post(B + "/report", headers=admin_headers,
                    json={"target": "modules", "title": "T", "what": "W", "expected": "", "steps": ""})
    assert r.status_code == 200 and r.json() == {"number": 3, "url": "u"}
    assert got == {"target": "modules", "title": "T", "what": "W"}


def test_fehler_melden_fehlercode(client, admin_headers, clean, monkeypatch):
    from backend import report

    async def nope(*a):
        raise submit.SubmitError("labor_github_not_connected")
    monkeypatch.setattr(report, "report", nope)
    r = client.post(B + "/report", headers=admin_headers, json={"target": "core", "title": "T", "what": "W"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_github_not_connected"


def test_einreichungen_liste_und_aktualisieren(client, admin_headers, clean, monkeypatch):
    seen = []

    async def fake_refresh():
        seen.append(1)
    monkeypatch.setattr(submit, "refresh", fake_refresh)
    monkeypatch.setattr(submit, "list_submissions", lambda: [{"id": 1, "kind": "pr", "number": 7}])
    assert client.get(B + "/submissions", headers=admin_headers).json() == {"items": [{"id": 1, "kind": "pr",
                                                                                       "number": 7}]}
    assert client.post(B + "/submissions/refresh", headers=admin_headers, json={}).status_code == 200
    assert seen == [1]


def test_einreichen_steht_in_auftraegen():
    assert "submit" in jobs.JOBS


@pytest.fixture
def user_with_module_grant(db_ready):
    from hydrahive.access import grants
    from hydrahive.api.middleware.users import get_by_username
    uid = get_by_username("testuser")["user_id"]
    grants.grant("module.hydralabor", "user", uid, "use", actor_id="test")
    yield
    grants.revoke("module.hydralabor", "user", uid, actor_id="test")


@pytest.mark.parametrize(("method", "path"), [("get", "/github"), ("post", "/github/connect"),
                                              ("post", "/github/disconnect"), ("post", "/report"),
                                              ("get", "/submissions")])
def test_auch_mit_modulfreigabe_nur_admins(client, user_headers, clean, user_with_module_grant, method, path):
    kw = {"json": {"target": "core", "title": "T", "what": "W"}} if method == "post" else {}
    r = getattr(client, method)(B + path, headers=user_headers, **kw)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "admin_only"


def test_trennen_loescht_wirklich(client, admin_headers, clean):
    from hydrahive.credentials import _crypto
    from hydrahive.db.connection import db
    from hydrahive.settings import settings
    with db() as c:
        c.execute("INSERT OR REPLACE INTO module_hydralabor_github (id, token_enc, login, user_id) VALUES (1, ?, 'n', 1)",
                  (_crypto.encrypt("gho_x", settings.data_dir),))
        c.commit()
    r = client.post(B + "/github/disconnect", headers=admin_headers, json={})
    assert r.json()["connected"] is False and github_auth.token() == ""


def test_neues_einreichen_loescht_altes_ergebnis(client, admin_headers, clean, monkeypatch):
    """Während des neuen Laufs darf nicht der alte PR-Link als Ergebnis dastehen."""
    during = {}

    async def slow(target, title, body, *, report):
        during.update(state.get()["submit_out"])
        return {"number": 9, "url": "u"}
    monkeypatch.setattr(submit, "submit", slow)
    state.set_step("ready")
    state.set_submit_out({"number": 1, "url": "alt"})
    client.post(B + "/submit", headers=admin_headers, json={"target": "core", "title": "T", "body": ""})
    wait_idle()
    assert during == {}
    assert state.get()["submit_out"] == {"number": 9, "url": "u"}
    assert state.get()["submit_in"]["title"] == "T"
