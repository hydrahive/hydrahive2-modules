"""App-Verwaltung: Aufträge mit incus-Attrappe und Schnittstellen. Ohne echten Fernseher."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, network, store_jobs

B = "/api/modules/tvwerkstatt"
GTV = "com.google.android.apps.tv.launcherx"
OK = "__TVW__ state=device\n"
LIST = (OK + "__TVW__ app|tv.emby.embyatv|250500|2.5.05g|com.android.vending|0\n"
        "__TVW__ app|com.gathin.tvhome|13|3.4||0\n__TVW__ app|com.side.load|1|1.0|null|0\n")


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
                     "current_home, created_by) VALUES ('t1', 'Wohnzimmer', '192.168.178.201', 34, 'google_tv', ?, "
                     "'com.gathin.tvhome', 'boss')", (GTV,))
        conn.commit()
    a = fake_incus.exec_answers
    a["pm list packages -3 | sed"] = (0, LIST)
    a["am start -a android.intent.action.VIEW"] = (0, OK + "Starting: Intent { act=android.intent.action.VIEW }\n")
    a["pm uninstall"] = (0, OK + "Success\n__TVW__ gone\n")
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _go(kind: str, runner) -> dict:
    job_id = jobs.begin(kind, "t1", "boss", "container")
    run(runner(job_id, "t1"))
    return jobs.last_job(kind, "t1")


def test_lesen_und_ansicht(env):
    assert _go("store_read", store_jobs.run_read)["state"] == "done"
    apps = {a["package"]: a for a in store_jobs.view("t1")["apps"]}
    assert apps["tv.emby.embyatv"]["store"] is True and apps["tv.emby.embyatv"]["locked"] is False
    assert apps["com.gathin.tvhome"]["locked"] is True and apps["com.side.load"]["store"] is False
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_store_oeffnen_und_suchen(env):
    assert _go("store_open", store_jobs.runner_open("tv.emby.embyatv", None))["state"] == "done"
    assert _go("store_open", store_jobs.runner_open(None, "Kodi"))["state"] == "done"
    calls = [b for b in env.exec_log if "am start" in b]
    assert "market://details?id=tv.emby.embyatv" in calls[0] and "market://search?q=Kodi" in calls[1]


def test_store_nicht_da(env):
    env.exec_answers["am start -a android.intent.action.VIEW"] = (0, OK + "Error: Activity not started\n")
    assert _go("store_open", store_jobs.runner_open(None, "Kodi"))["error_code"] == "tvw_store_failed"


def test_deinstallieren_liest_danach_neu(env):
    j = _go("store_uninstall", store_jobs.runner_uninstall("t1", "com.side.load"))
    assert (j["state"], j["error_code"]) == ("done", "")
    assert any("pm uninstall com.side.load" in b for b in env.exec_log)
    assert store_jobs.view("t1") is not None


def test_deinstallieren_vorinstalliert_lehnt_das_geraet_ab(env):
    env.exec_answers["pm uninstall"] = (0, OK + "__TVW__ not_user\n")
    assert _go("store_uninstall", store_jobs.runner_uninstall("t1", "com.tcl.guard"))["error_code"] == \
        "tvw_store_not_user_app"


@pytest.mark.parametrize("pkg", ["com.gathin.tvhome", GTV, "com.android.vending", "com.android.systemui"])
def test_geschuetztes_nie_deinstallieren(env, pkg):
    from backend import store
    with pytest.raises(store.TvwStoreError) as e:
        store_jobs.runner_uninstall("t1", pkg)
    assert e.value.code == "tvw_store_locked"


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_nur_admins(client, user_headers, env):
    assert client.get(B + "/devices/t1/store", headers=user_headers).status_code == 403
    for path, body in (("/store/read", {}), ("/store/open", {"query": "Kodi"}),
                       ("/store/uninstall", {"confirm": True, "package": "com.side.load"})):
        assert client.post(B + "/devices/t1" + path, json=body, headers=user_headers).status_code == 403


def test_eingaben_an_der_schnittstelle(client, admin_headers, env):
    def post(path, body):
        r = client.post(B + "/devices/t1" + path, json=body, headers=admin_headers)
        return r.status_code, r.json().get("detail", {}).get("code") if r.status_code == 400 else None
    assert post("/store/open", {}) == (400, "tvw_store_bad_query")
    assert post("/store/open", {"query": "a", "package": "tv.emby.embyatv"}) == (400, "tvw_store_bad_query")
    assert post("/store/open", {"query": "x; reboot"}) == (400, "tvw_store_bad_query")
    assert post("/store/open", {"package": "kaputt"}) == (400, "tvw_store_bad_package")
    assert post("/store/uninstall", {"package": "com.side.load"}) == (400, "tvw_confirm_required")
    assert post("/store/uninstall", {"confirm": True, "package": "com.gathin.tvhome"}) == (400, "tvw_store_locked")
    assert post("/store/open", {"query": "Kodi"})[0] == 202


def test_zustand(client, admin_headers, env):
    r = client.get(B + "/devices/t1/store", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"view": None, "job": None}
    assert client.get(B + "/devices/nix/store", headers=admin_headers).status_code == 404
