"""G2: Auftrag „App bauen“ und Schnittstelle (bauen, herunterladen, Stand) mit incus-Attrappe (PLAN-APP.md)."""
from __future__ import annotations

import asyncio

import pytest
from backend import app_build, build_jobs, container, jobs, network, source
from test_tvw_app_build import COLLECT, SHA, SIG

B = "/api/modules/tvwerkstatt"


def run(coro):
    return asyncio.run(coro)


# --- Auftrag ------------------------------------------------------------------------------------------------------

@pytest.fixture
def env(fake_incus, db_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(app_build, "apk_dir", lambda: tmp_path / "app")
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    fake_incus.exec_answers["__TVW__ sha256"] = (0, COLLECT)
    fake_incus.exec_answers["assembleRelease"] = (0, "BUILD SUCCESSFUL in 9s\n")
    fake_incus.pull_bytes = b"PK\x03\x04erfundene-app"
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _build(env, sha_of_pulled=True):
    import hashlib
    if sha_of_pulled:
        good = hashlib.sha256(env.pull_bytes).hexdigest()
        env.exec_answers["__TVW__ sha256"] = (0, COLLECT.replace(SHA, good))
    job_id = jobs.begin("app_build", "hydra-app", "boss", "container")
    run(app_build.run(job_id))
    return jobs.last_job("app_build"), next(b for b in build_jobs.state.builds() if b["part"] == "hydra-app")


def test_bau_ganz(env):
    j, b = _build(env)
    assert (j["state"], j["error_code"]) == ("done", "")
    assert (b["state"], b["package"], b["version"], b["signer"], b["permissions"]) == (
        "done", "io.hydrahive.app", "0.1.0 (1)", SIG, "INTERNET")
    assert b["commit_id"] == app_build.source_tar()[1]                  # Stand = Prüfsumme des Quelltexts
    assert app_build.apk_path().read_bytes() == env.pull_bytes
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_reihenfolge_holen_pruefen_entpacken_bauen_lesen(env):
    _build(env)
    keys = ("FETCH_HEAD", "sha256sum -c", "tar -x -C", "assembleRelease", "aapt2")
    order = [next(k for k in keys if k in b) for b in env.exec_log if any(k in b for k in keys)]
    assert order == list(keys)


def test_quelltext_geht_per_stdin_in_den_container(env):
    _build(env)
    assert env.stdin_for("tar -x -C") == app_build.source_tar()[0]


def test_geholte_app_mit_anderer_pruefsumme_wird_verworfen(env):
    j, b = _build(env, sha_of_pulled=False)
    assert (j["state"], j["error_code"]) == ("failed", "tvw_build_unreadable")
    assert b["state"] == "failed" and app_build.apk_path() is None


def test_tests_rot_heisst_kein_bau(env):
    env.exec_answers["assembleRelease"] = (1, "LogicTest > codeWirdGesaeubert FAILED\n")
    j, b = _build(env)
    assert (j["step"], j["error_code"]) == ("build", "tvw_build_failed")
    assert "codeWirdGesaeubert" in b["log_tail"] and app_build.apk_path() is None


def test_gradle_falsch_baut_nicht(env):
    env.exec_answers["sha256sum -c"] = (source.RC_MISMATCH, "Gradle-Wrapper passt nicht")
    j, _ = _build(env)
    assert (j["step"], j["error_code"]) == ("verify", "tvw_source_mismatch")
    assert not any("assembleRelease" in x for x in env.exec_log)


def test_alte_app_bleibt_bis_eine_neue_fertig_ist(env):
    _build(env)
    first = app_build.apk_path().read_bytes()
    env.exec_answers["assembleRelease"] = (1, "boom\n")
    _build(env)
    assert app_build.apk_path().read_bytes() == first


def test_alte_app_bleibt_wenn_das_holen_scheitert(env):
    _build(env)
    first = app_build.apk_path().read_bytes()
    env.fail["file pull"] = "Error: not found"
    j, _ = _build(env)
    assert j["error_code"] == "tvw_build_unreadable"
    assert app_build.apk_path().read_bytes() == first
    assert not (app_build.apk_dir() / "hydrahive.apk.tmp").exists()


# --- Schnittstelle ------------------------------------------------------------------------------------------------

def test_bauen_und_herunterladen_nur_admins(client, user_headers, env):
    assert client.post(B + "/app/build", json={}, headers=user_headers).status_code == 403
    assert client.get(B + "/app/apk", headers=user_headers).status_code == 403


def test_bauen_startet(client, admin_headers, env):
    r = client.post(B + "/app/build", json={}, headers=admin_headers)
    assert r.status_code == 202 and r.json()["job_id"]


def test_bauen_ohne_werkstatt_409(client, admin_headers, env):
    env.containers.pop("hh-tvwerkstatt")
    r = client.post(B + "/app/build", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "tvw_not_set_up"


def test_herunterladen_ohne_bau_404(client, admin_headers, env):
    r = client.get(B + "/app/apk", headers=admin_headers)
    assert r.status_code == 404 and r.json()["detail"]["code"] == "tvw_app_no_build"


def test_herunterladen_nach_bau(client, admin_headers, env):
    _build(env)
    r = client.get(B + "/app/apk", headers=admin_headers)
    assert r.status_code == 200 and r.content == env.pull_bytes
    assert r.headers["content-type"] == "application/vnd.android.package-archive"
    assert 'filename="hydrahive-0.1.0.apk"' in r.headers["content-disposition"]


def test_stand_zeigt_letzten_app_bau(client, admin_headers, env):
    _build(env)
    d = client.get(B + "/app/devices", headers=admin_headers).json()
    assert d["build"]["state"] == "done" and d["apk"]["version"] == "0.1.0 (1)" and d["apk"]["size"] == 20332


def test_routen_pruefen_admin_auch_selbst():
    """Zweite Schicht neben der Prüfung des Kerns (module.tvwerkstatt): jede Route verlangt selbst einen Admin."""
    from backend import routes_app_build
    for r in routes_app_build.router.routes:
        names = {d.call.__name__ for d in r.dependant.dependencies}
        assert "require_admin_principal" in names, r.path
