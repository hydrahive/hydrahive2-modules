"""Baustein 4: Quelle am festen Commit, Prüfsummen, Bau, Auswertung der App, Auftrag und Schnittstelle."""
from __future__ import annotations

import asyncio

import pytest
from backend import build, build_jobs, container, jobs, network, source

B = "/api/modules/tvwerkstatt"
SHA = "c6d21b45a3238d2b56e0d22a08bd0f2a52a97d71d10784d3264078ab84b92780"
SIG = "7676576025d19d8297a575312fbb07d5d9466b6b088c4524458328753ec70547"
COLLECT = (f"__TVW__ sha256={SHA}\n__TVW__ size=588009\n__TVW__ badging=package: name='com.gathin.tvhome' "
           f"versionCode='13' versionName='3.4' platformBuildVersionName='14'\n__TVW__ signer={SIG}\n"
           f"__TVW__ keystore={SIG}\n")


def run(coro):
    return asyncio.run(coro)


# --- rein -----------------------------------------------------------------------------------------------------

def test_quelle_fest_an_einem_vollen_commit():
    assert len(source.COMMIT) == 40 and all(c in "0123456789abcdef" for c in source.COMMIT)
    assert source.COMMIT in source.FETCH_SCRIPT and source.REPO in source.FETCH_SCRIPT
    assert "git diff --quiet HEAD" in source.FETCH_SCRIPT                 # veränderte Quelle wird nicht gebaut


def test_gradle_pruefsummen_vor_dem_bau():
    v = source.VERIFY_SCRIPT
    assert source.WRAPPER_SHA256 in v and source.DIST_SHA256 in v and "sha256sum -c" in v
    assert f"exit {source.RC_MISMATCH}" in v


def test_bau_ohne_daemon_und_mit_protokoll():
    assert "--no-daemon" in build.BUILD_SCRIPT and "assembleRelease" in build.BUILD_SCRIPT
    assert "sudo" not in build.BUILD_SCRIPT


def test_auswertung():
    assert build.evaluate(build.parse(COLLECT)) == {"sha256": SHA, "size": 588009, "package": "com.gathin.tvhome",
                                                    "version": "3.4 (13)", "signer": SIG}


def test_fremde_signatur():
    vals = build.parse(COLLECT.replace(f"keystore={SIG}", "keystore=" + "0" * 64))
    with pytest.raises(build.TvwBuildError) as e:
        build.evaluate(vals)
    assert e.value.code == "tvw_signer_mismatch"


def test_falsches_paket():
    with pytest.raises(build.TvwBuildError) as e:
        build.evaluate(build.parse(COLLECT.replace("com.gathin.tvhome", "com.example.boese")))
    assert e.value.code == "tvw_build_unexpected"


@pytest.mark.parametrize("kaputt", ["sha256=xyz", "size=viel", "badging=nichts"])
def test_unlesbar(kaputt):
    key = kaputt.split("=")[0]
    lines = [ln if not ln.startswith(f"__TVW__ {key}=") else f"__TVW__ {kaputt}" for ln in COLLECT.splitlines()]
    with pytest.raises(build.TvwBuildError) as e:
        build.evaluate(build.parse("\n".join(lines)))
    assert e.value.code == "tvw_build_unreadable"


def test_protokoll_bereinigt_und_gekuerzt():
    log = build.clean_log("\x1b[31mFEHLER\x1b[0m in hh-tvwerkstatt\n" + "\n".join(f"Zeile {i}" for i in range(500)))
    assert "\x1b" not in log and "hh-tvwerkstatt" not in log
    assert log.endswith("Zeile 499") and len(log.splitlines()) <= build.LOG_LINES


# --- Auftrag --------------------------------------------------------------------------------------------------

@pytest.fixture
def env(fake_incus, db_ready, monkeypatch):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    fake_incus.exec_answers["__TVW__ sha256"] = (0, COLLECT)
    fake_incus.exec_answers["assembleRelease"] = (0, "BUILD SUCCESSFUL in 38s\n")
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _build() -> tuple[dict, dict]:
    job_id = jobs.begin("build", "launcher", "boss", "container")
    run(build_jobs.run_build(job_id))
    return jobs.last_job("build"), build_jobs.state.builds()[0]


def test_bau_ganz(env):
    j, b = _build()
    assert (j["state"], j["error_code"]) == ("done", "")
    assert (b["state"], b["sha256"], b["version"], b["size"], b["signer"], b["commit_id"]) == (
        "done", SHA, "3.4 (13)", 588009, SIG, source.COMMIT)
    assert "BUILD SUCCESSFUL" in b["log_tail"]
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_reihenfolge_holen_pruefen_bauen_lesen(env):
    _build()
    order = [next(k for k in ("FETCH_HEAD", "sha256sum -c", "assembleRelease", "aapt2") if k in b)
             for b in env.exec_log if any(k in b for k in ("FETCH_HEAD", "sha256sum -c", "assembleRelease", "aapt2"))]
    assert order == ["FETCH_HEAD", "sha256sum -c", "assembleRelease", "aapt2"]


def test_bau_als_nutzer_ohne_root(env):
    _build()
    bau = next(c for c in env.calls if c[0] == "exec" and "assembleRelease" in " ".join(c))
    assert bau[bau.index("--user") + 1] == "1000"


def test_pruefsumme_gradle_falsch_baut_nicht(env):
    env.exec_answers["sha256sum -c"] = (source.RC_MISMATCH, "Gradle-Wrapper passt nicht")
    j, b = _build()
    assert (j["state"], j["step"], j["error_code"]) == ("failed", "verify", "tvw_source_mismatch")
    assert b["state"] == "failed"
    assert not any("assembleRelease" in x for x in env.exec_log)


def test_bau_scheitert_mit_protokoll(env):
    env.exec_answers["assembleRelease"] = (1, "FAILURE: Build failed with an exception.\n* What went wrong: boom\n")
    j, b = _build()
    assert (j["step"], j["error_code"]) == ("build", "tvw_build_failed")
    assert "What went wrong" in j["error_detail"] and "What went wrong" in b["log_tail"]
    assert env.containers["hh-tvwerkstatt"]["running"] is False             # auch nach Fehler angehalten


def test_holen_scheitert(env):
    env.exec_answers["FETCH_HEAD"] = (128, "fatal: unable to access")
    j, _ = _build()
    assert (j["step"], j["error_code"]) == ("fetch", "tvw_source_failed")


def test_ohne_werkstatt(env):
    env.containers.pop("hh-tvwerkstatt")
    j = jobs.last_job("build") or {}
    job_id = jobs.begin("build", "launcher", "boss", "container")
    run(build_jobs.run_build(job_id))
    j = jobs.last_job("build")
    assert j["error_code"] == "tvw_not_set_up" and build_jobs.state.builds() == []


def test_unterbrochener_bau_wird_als_gescheitert_gezeigt(client, admin_headers, env):
    jobs.begin("build", "launcher", "boss", "container")
    build_jobs._new_build(source.source_id())
    jobs.reset()                                                            # wie ein Neustart
    d = client.get(B + "/state", headers=admin_headers).json()
    assert d["build"]["error_code"] == "tvw_interrupted"
    assert d["builds"][0]["state"] == "failed"


# --- Schnittstelle --------------------------------------------------------------------------------------------

def test_bauen_nur_admins(client, user_headers, env):
    assert client.post(B + "/build", json={}, headers=user_headers).status_code == 403


def test_bauen_startet(client, admin_headers, env):
    r = client.post(B + "/build", json={}, headers=admin_headers)
    assert r.status_code == 202 and r.json()["job_id"]
    assert client.get(B + "/state", headers=admin_headers).json()["build"]["job_id"] == r.json()["job_id"]


def test_bauen_ohne_werkstatt_409(client, admin_headers, env):
    env.containers.pop("hh-tvwerkstatt")
    r = client.post(B + "/build", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "tvw_not_set_up"


def test_bauen_waehrend_anderem_auftrag_409(client, admin_headers, env):
    jobs.begin("probe", "d1", "boss", "network")
    r = client.post(B + "/build", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "tvw_busy"
