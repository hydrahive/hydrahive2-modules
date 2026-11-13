"""Baustein 6: Aufträge Aufspielen / Zurück mit incus-Attrappe (kein echter Fernseher), Schnittstellen."""
from __future__ import annotations

import asyncio

import pytest
from backend import build_jobs, container, install_jobs, jobs, network, source

B = "/api/modules/tvwerkstatt"
SHA = "c6d21b45a3238d2b56e0d22a08bd0f2a52a97d71d10784d3264078ab84b92780"
OURS = "__TVW__ home=com.gathin.tvhome/.MainActivity\n"
STOCK = "__TVW__ home=com.google.android.tvlauncher/.MainActivity\n"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(fake_incus, db_ready, monkeypatch):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, sdk, stock_home, current_home, "
                     "created_by) VALUES ('d1', 'Wohnzimmer', '192.168.178.200', 28, 'com.google.android.tvlauncher', "
                     "'com.google.android.tvlauncher', 'boss')")
        conn.commit()
    bid = build_jobs._new_build(source.source_id())
    build_jobs._set_build(bid, state="done", sha256=SHA, package="com.gathin.tvhome", version="3.4 (13)")
    a = fake_incus.exec_answers
    a["__TVW__ sha256"] = (0, f"__TVW__ sha256={SHA}\n")
    a["pm install -r"] = (0, "__TVW__ state=device\nSuccess\n")
    a["am start -W"] = (0, "__TVW__ state=device\nStatus: ok\nComplete\n")
    a["pm disable-user"] = (0, "__TVW__ state=device\n" + OURS)
    a["pm enable --user 0"] = (0, "__TVW__ state=device\n" + STOCK)
    a["query-activities"] = (0, "__TVW__ state=device\n__TVW__ claims=com.google.android.tvlauncher,\n" + STOCK)
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _go(kind: str) -> dict:
    job_id = jobs.begin(kind, "d1", "boss", "container")
    run((install_jobs.run_install if kind == "install" else install_jobs.run_restore)(job_id, "d1"))
    return jobs.last_job(kind, "d1")


def _dev() -> dict:
    return next(d for d in install_jobs.state.devices() if d["device_id"] == "d1")


def _installed() -> list:
    from hydrahive.db.connection import db
    with db() as conn:
        return [tuple(r) for r in conn.execute("SELECT device_id, package, sha256 FROM module_tvwerkstatt_installed")]


def test_aufspielen_ganz(env):
    j = _go("install")
    assert (j["state"], j["error_code"]) == ("done", "")
    assert _dev()["current_home"] == "com.gathin.tvhome"
    assert _installed() == [("d1", "com.gathin.tvhome", SHA)]
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_reihenfolge_pruefen_aufspielen_starten_umschalten(env):
    _go("install")
    keys = ("__TVW__ sha256", "query-activities", "pm install -r", "am start -W", "pm disable-user")
    order = [next(k for k in keys if k in b) for b in env.exec_log if any(k in b for k in keys)]
    assert order == list(keys)


def test_aufspielen_scheitert_original_bleibt_unberuehrt(env):
    env.exec_answers["pm install -r"] = (0, "__TVW__ state=device\nFailure [INSTALL_FAILED_INSUFFICIENT_STORAGE]\n")
    j = _go("install")
    assert (j["step"], j["error_code"], j["error_detail"]) == ("push", "tvw_install_failed",
                                                                 "INSTALL_FAILED_INSUFFICIENT_STORAGE")
    assert not any("pm disable-user" in b or "am start" in b for b in env.exec_log)


def test_start_scheitert_original_bleibt_unberuehrt(env):
    env.exec_answers["am start -W"] = (0, "__TVW__ state=device\nError: Activity not started\n")
    j = _go("install")
    assert j["error_code"] == "tvw_home_not_started"
    assert not any("pm disable-user" in b for b in env.exec_log)


def test_home_springt_nicht_um_automatisch_zurueck(env):
    env.exec_answers["pm disable-user"] = (0, "__TVW__ state=device\n__TVW__ home=android\n")
    j = _go("install")
    assert (j["step"], j["error_code"]) == ("restore", "tvw_home_not_switched")
    assert any("pm enable --user 0 com.google.android.tvlauncher" in b for b in env.exec_log)
    assert _dev()["current_home"] == "com.google.android.tvlauncher" and _installed() == []


def test_rueckweg_klappt_auch_nicht(env):
    env.exec_answers["pm disable-user"] = (0, "__TVW__ state=device\n__TVW__ home=android\n")
    env.exec_answers["pm enable --user 0"] = (0, "__TVW__ state=device\n__TVW__ home=android\n")
    assert _go("install")["error_code"] == "tvw_restore_incomplete"


def test_gebaute_app_veraendert(env):
    env.exec_answers["__TVW__ sha256"] = (0, "__TVW__ sha256=" + "0" * 64 + "\n")
    j = _go("install")
    assert (j["step"], j["error_code"]) == ("verify", "tvw_build_changed")
    assert not any("pm install" in b for b in env.exec_log)


def test_ohne_bau(env):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_builds SET state = 'failed'")
        conn.commit()
    assert _go("install")["error_code"] == "tvw_no_build"


def test_unbekanntes_original_wird_nicht_angefasst(env):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_devices SET stock_home = ''")
        conn.commit()
    assert _go("install")["error_code"] == "tvw_no_stock_home"
    assert not any("pm install" in b for b in env.exec_log)


def test_freigabe_fehlt(env):
    env.exec_answers["pm install -r"] = (0, "__TVW__ state=unauthorized\n")
    assert _go("install")["error_code"] == "tvw_adb_unauthorized"


def test_zurueck_zum_original(env):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_devices SET current_home = 'com.gathin.tvhome'")
        conn.commit()
    j = _go("restore")
    assert (j["state"], j["error_code"]) == ("done", "")
    assert _dev()["current_home"] == "com.google.android.tvlauncher"
    assert not any("pm uninstall" in b for b in env.exec_log)


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_nur_admins(client, user_headers, env):
    for path in ("/devices/d1/install", "/devices/d1/restore"):
        assert client.post(B + path, json={"confirm": True}, headers=user_headers).status_code == 403


@pytest.mark.parametrize("path", ["/devices/d1/install", "/devices/d1/restore"])
def test_ohne_rueckfrage_nichts(client, admin_headers, env, path):
    r = client.post(B + path, json={}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_confirm_required"
    assert jobs.last_job("install", "d1") is None and jobs.last_job("restore", "d1") is None


def test_aufspielen_startet_und_zustand_zeigt_es(client, admin_headers, env):
    r = client.post(B + "/devices/d1/install", json={"confirm": True}, headers=admin_headers)
    assert r.status_code == 202
    dev = client.get(B + "/state", headers=admin_headers).json()["devices"][0]
    assert dev["action"]["job_id"] == r.json()["job_id"] and dev["action"]["kind"] == "install"


def test_unbekanntes_geraet(client, admin_headers, env):
    r = client.post(B + "/devices/gibtsnicht/install", json={"confirm": True}, headers=admin_headers)
    assert r.status_code == 404
