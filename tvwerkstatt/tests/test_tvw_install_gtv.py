"""Aufspielen auf Google TV (TCL, Google TV 14): Einrichtungs-Helfer vor dem Original abschalten, Rückweg schaltet ihn
wieder ein. incus-Attrappe, kein echter Fernseher."""
from __future__ import annotations

import asyncio

import pytest
from backend import build_jobs, container, guard, install_jobs, jobs, network, source

SHA = "c6d21b45a3238d2b56e0d22a08bd0f2a52a97d71d10784d3264078ab84b92780"
GTV = "com.google.android.apps.tv.launcherx"
OK = "__TVW__ state=device\n"
STOCK = f"__TVW__ home={GTV}/.home.HomeActivity\n"
OURS = "__TVW__ home=com.gathin.tvhome/.MainActivity\n"
READ = (OK + f"__TVW__ claims={GTV},{guard.SETUP},com.android.tv.settings,\n"
        "__TVW__ wifi_owners=com.android.tv.settings,\n__TVW__ wifi_none=0\n" + STOCK)


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
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, sdk, kind, stock_home, "
                     "current_home, created_by) VALUES ('t1', 'Wohnzimmer', '192.168.178.201', 34, 'google_tv', ?, ?, "
                     "'boss')", (GTV, GTV))
        conn.commit()
    bid = build_jobs._new_build(source.source_id())
    build_jobs._set_build(bid, state="done", sha256=SHA, package="com.gathin.tvhome", version="3.4 (13)")
    a = fake_incus.exec_answers
    a["__TVW__ sha256"] = (0, f"__TVW__ sha256={SHA}\n")
    a["query-activities"] = (0, READ)
    a[f"pm disable-user --user 0 {guard.SETUP}"] = (0, OK + STOCK)
    a["pm install -r"] = (0, OK + "Success\n")
    a["am start -W"] = (0, OK + "Status: ok\nComplete\n")
    a[f"pm disable-user --user 0 {GTV}"] = (0, OK + OURS)
    a["pm enable --user 0"] = (0, OK + STOCK)
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _go(kind: str) -> dict:
    job_id = jobs.begin(kind, "t1", "boss", "container")
    run((install_jobs.run_install if kind == "install" else install_jobs.run_restore)(job_id, "t1"))
    return jobs.last_job(kind, "t1")


def _row() -> tuple:
    from hydrahive.db.connection import db
    with db() as conn:
        return tuple(conn.execute("SELECT current_home, extra_disabled FROM module_tvwerkstatt_devices").fetchone())


def _first(env, needle: str) -> int:
    return next(i for i, b in enumerate(env.exec_log) if needle in b)


def test_helfer_vor_dem_original_und_vermerkt(env):
    j = _go("install")
    assert (j["state"], j["error_code"]) == ("done", "")
    assert _first(env, f"disable-user --user 0 {guard.SETUP}") < _first(env, "pm install -r") \
        < _first(env, f"disable-user --user 0 {GTV}")
    assert _row() == ("com.gathin.tvhome", guard.SETUP)


def test_zurueck_schaltet_helfer_wieder_ein_und_vermerk_faellt(env):
    _go("install")
    j = _go("restore")
    assert (j["state"], j["error_code"]) == ("done", "")
    assert any(f"pm enable --user 0 {guard.SETUP}" in b for b in env.exec_log)
    assert _row() == (GTV, "")


def test_wlan_gehoert_dem_helfer_nichts_passiert(env):
    env.exec_answers["query-activities"] = (0, READ.replace("wifi_owners=", f"wifi_owners={guard.SETUP},"))
    j = _go("install")
    assert (j["step"], j["error_code"]) == ("guard", "tvw_wifi_owned_by_setup")
    assert not any("disable-user" in b or "pm install" in b for b in env.exec_log)
    assert _row() == (GTV, "")


def test_home_springt_nach_helfer_ab_weg_zurueck(env):
    env.exec_answers[f"pm disable-user --user 0 {guard.SETUP}"] = (0, OK + "__TVW__ home=android\n")
    j = _go("install")
    assert j["error_code"] == "tvw_guard_failed" and "zurück:" in j["error_detail"]
    assert any(f"pm enable --user 0 {guard.SETUP}" in b for b in env.exec_log)
    assert not any("pm install" in b for b in env.exec_log)
    assert _row() == (GTV, "")


def test_aufspielen_scheitert_helfer_kommt_zurueck(env):
    env.exec_answers["pm install -r"] = (0, OK + "Failure [INSTALL_FAILED_INSUFFICIENT_STORAGE]\n")
    j = _go("install")
    assert j["error_code"] == "tvw_install_failed"
    assert any(f"pm enable --user 0 {guard.SETUP}" in b for b in env.exec_log)
    assert not any(f"disable-user --user 0 {GTV}" in b for b in env.exec_log)
    assert _row() == (GTV, "")


def test_unerwarteter_fehler_nach_vorpruefung_auch_zurueck(env, monkeypatch):
    async def boom(*_a, **_k):
        raise OSError("weg")
    monkeypatch.setattr(install_jobs, "_hand_over", boom)
    j = _go("install")
    assert (j["state"], j["error_code"]) == ("failed", "tvw_install_failed")
    assert any(f"pm enable --user 0 {guard.SETUP}" in b for b in env.exec_log)


def test_rueckweg_scheitert_ehrlich_und_vermerk_bleibt(env):
    env.exec_answers["pm install -r"] = (0, OK + "Failure [INSTALL_FAILED_INSUFFICIENT_STORAGE]\n")
    env.exec_answers["pm enable --user 0"] = (0, OK + "__TVW__ home=android\n")
    assert _go("install")["error_code"] == "tvw_restore_incomplete"
    assert _row()[1] == guard.SETUP


def test_vermerk_von_frueher_kommt_beim_zurueck_mit(env):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("UPDATE module_tvwerkstatt_devices SET current_home = 'com.gathin.tvhome', extra_disabled = ?",
                     (guard.SETUP,))
        conn.commit()
    assert _go("restore")["error_code"] == ""
    assert any(f"pm enable --user 0 {guard.SETUP}" in b for b in env.exec_log)
