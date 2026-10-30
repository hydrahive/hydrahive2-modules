"""Hydra-Labor L3: Schnittstellen der Probe – nur Admins, Aufträge im Hintergrund, Stand."""
from __future__ import annotations

import pytest
from backend import jobs, probe, state

B = "/api/modules/hydralabor"


@pytest.fixture
def ready(db_ready):
    state.clear()
    state.set_step("ready")
    yield
    state.clear()


@pytest.fixture
def started(monkeypatch):
    calls = []

    def fake_start(name):
        calls.append(name)
        return state.begin(name)
    monkeypatch.setattr(jobs, "start", fake_start)
    return calls


@pytest.mark.parametrize(("method", "path"), [("get", "/probe"), ("post", "/probe/build"), ("post", "/probe/start"),
                                              ("post", "/probe/stop"), ("post", "/probe/open")])
def test_nur_admins(client, user_headers, ready, method, path):
    kw = {"json": {}} if method == "post" else {}
    assert getattr(client, method)(B + path, headers=user_headers, **kw).status_code == 403


@pytest.fixture
def user_with_module_grant(db_ready):
    from hydrahive.access import grants
    from hydrahive.api.middleware.users import get_by_username
    uid = get_by_username("testuser")["user_id"]
    grants.grant("module.hydralabor", "user", uid, "use", actor_id="test")
    yield
    grants.revoke("module.hydralabor", "user", uid, actor_id="test")


@pytest.mark.parametrize(("method", "path"), [("get", "/probe"), ("post", "/probe/build"), ("post", "/probe/start"),
                                              ("post", "/probe/stop"), ("post", "/probe/open")])
def test_auch_mit_modulfreigabe_nur_admins(client, user_headers, ready, user_with_module_grant, method, path):
    kw = {"json": {}} if method == "post" else {}
    r = getattr(client, method)(B + path, headers=user_headers, **kw)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "admin_only"


@pytest.mark.parametrize("path", ["/probe", "/probe/build", "/probe/start", "/probe/stop"])
def test_ohne_anmeldung(client, ready, path):
    r = client.get(B + path) if path == "/probe" else client.post(B + path, json={})
    assert r.status_code == 401


@pytest.mark.parametrize(("path", "job"), [("/probe/build", "probe_build"), ("/probe/start", "probe_start"),
                                           ("/probe/stop", "probe_stop")])
def test_auftrag_im_hintergrund(client, admin_headers, ready, started, path, job):
    r = client.post(B + path, headers=admin_headers, json={})
    assert r.status_code == 202 and r.json() == {"started": job}
    assert started == [job]


@pytest.mark.parametrize("path", ["/probe/build", "/probe/start", "/probe/stop"])
def test_nur_wenn_fertig(client, admin_headers, db_ready, started, path):
    state.clear()
    r = client.post(B + path, headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_not_ready"
    assert started == []


def test_besetzt(client, admin_headers, ready, started):
    state.begin("test")
    r = client.post(B + "/probe/build", headers=admin_headers, json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "labor_busy"


def test_stand(client, admin_headers, ready, monkeypatch):
    async def fake():
        return {"built": True, "running": True, "user": "admin", "password": "pw_123456", "port": 8443, "open": True}
    monkeypatch.setattr(probe, "status", fake)
    r = client.get(B + "/probe", headers=admin_headers)
    assert r.status_code == 200 and r.json()["password"] == "pw_123456" and r.json()["running"] is True


def test_stand_ohne_labor(client, admin_headers, db_ready, monkeypatch):
    state.clear()

    async def boom():
        raise AssertionError("darf nicht ins Labor schauen")
    monkeypatch.setattr(probe, "status", boom)
    r = client.get(B + "/probe", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"built": False, "running": False, "user": "admin", "password": "",
                                                 "port": 8443, "open": False}


def test_neue_teile_nicht_im_oeffentlichen_zustand(client, admin_headers, ready, monkeypatch):
    from backend import container

    async def no():
        return False
    monkeypatch.setattr(container, "running", no)
    state.mark_made("probe_site")
    body = client.get(B + "/state", headers=admin_headers).json()
    assert "made" not in body and "probe_site" not in str(body)
