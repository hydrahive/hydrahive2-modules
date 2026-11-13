"""Zusätze: Aufträge mit incus-Attrappe und Schnittstellen. Ohne echten Fernseher."""
from __future__ import annotations

import asyncio
import base64

import pytest
from backend import addon_jobs, container, jobs, network
from test_tvw_addons import BLOB

B = "/api/modules/tvwerkstatt"
OK = "__TVW__ state=device\n"
COLLECT = ("__TVW__ sha256=" + "b" * 64 + "\n__TVW__ size=1234\n__TVW__ sdk=26\n__TVW__ perms=android.permission.INTERNET,\n"
           "__TVW__ badging=package: name='io.example.koi' versionCode='1' versionName='1.0'\n")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(fake_incus, db_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(addon_jobs, "folder", lambda commit="": tmp_path / "addons")
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, sdk, kind, stock_home, "
                     "current_home, created_by) VALUES ('t1', 'Wohnzimmer', '192.168.178.201', 26, 'google_tv', "
                     "'com.google.android.apps.tv.launcherx', 'com.gathin.tvhome', 'boss')")
        conn.commit()
    a = fake_incus.exec_answers
    a["git fetch"] = (0, "")
    a["screenshot.jpg"] = (0, base64.b64encode(BLOB).decode() + "\n")
    a["gradle-wrapper.properties"] = (0, "__TVW__ gradle=8.9\n")
    a["assembleRelease"] = (0, "BUILD SUCCESSFUL\n")
    a["aapt2 dump badging"] = (0, COLLECT)
    a["pm install -r"] = (0, OK + "Success\n")
    a["pm uninstall"] = (0, OK + "Success\n__TVW__ gone\n")
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _go(kind: str, runner) -> dict:
    job_id = jobs.begin(kind, "t1", "boss", "container")
    run(runner(job_id, "t1"))
    return jobs.last_job(kind, "t1")


def _catalog():
    assert _go("addon_catalog", addon_jobs.run_catalog)["state"] == "done"


def test_katalog_laden_einmal_je_stand(env):
    _catalog()
    _catalog()
    assert sum("screenshot.jpg" in b for b in env.exec_log) == 1
    v = addon_jobs.view("t1")
    assert [i["id"] for i in v["items"]] == ["koi-pond", "remote-access"] and v["items"][0]["installed"] is None
    assert addon_jobs.image("koi-pond") is None                     # „jpg“ ist kein Bild → wird nicht gespeichert
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_bauen_und_installieren(env):
    _catalog()
    j = _go("addon_install", addon_jobs.runner_install("t1", "koi-pond"))
    assert (j["state"], j["error_code"]) == ("done", "")
    order = [k for b in env.exec_log for k in ("gradle-wrapper.properties", "assembleRelease", "aapt2", "pm install")
             if k in b]
    assert order == ["gradle-wrapper.properties", "assembleRelease", "aapt2", "pm install"]
    inst = addon_jobs.view("t1")["items"][0]["installed"]
    assert inst["version"] == "1.0 (1)" and inst["permissions"] == ["INTERNET"]


def test_gradle_nicht_freigegeben_kein_bau(env):
    _catalog()
    env.exec_answers["gradle-wrapper.properties"] = (4, "")
    j = _go("addon_install", addon_jobs.runner_install("t1", "koi-pond"))
    assert j["error_code"] == "tvw_source_mismatch"
    assert not any("assembleRelease" in b or "pm install" in b for b in env.exec_log)


def test_falsches_paket_nicht_installiert(env):
    _catalog()
    env.exec_answers["aapt2 dump badging"] = (0, COLLECT.replace("io.example.koi", "io.evil.app"))
    assert _go("addon_install", addon_jobs.runner_install("t1", "koi-pond"))["error_code"] == "tvw_build_unexpected"
    assert not any("pm install" in b for b in env.exec_log)


def test_android_zu_alt(env):
    _catalog()
    from backend import addons
    with pytest.raises(addons.TvwAddonError) as e:
        addon_jobs.runner_install("t1", "remote-access")            # minSdk 28, Fernseher 26
    assert e.value.code == "tvw_sdk_too_old"


def test_entfernen(env):
    _catalog()
    _go("addon_install", addon_jobs.runner_install("t1", "koi-pond"))
    j = _go("addon_remove", addon_jobs.runner_remove("t1", "koi-pond"))
    assert (j["state"], j["error_code"]) == ("done", "")
    assert addon_jobs.view("t1")["items"][0]["installed"] is None


def test_entfernen_scheitert(env):
    _catalog()
    env.exec_answers["pm uninstall"] = (0, OK + "Failure\n__TVW__ still\n")
    assert _go("addon_remove", addon_jobs.runner_remove("t1", "koi-pond"))["error_code"] == "tvw_addon_remove_failed"


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_nur_admins(client, user_headers, env):
    assert client.get(B + "/devices/t1/addons", headers=user_headers).status_code == 403
    for path in ("/catalog", "/install", "/remove"):
        r = client.post(B + "/devices/t1/addons" + path, json={"confirm": True, "addon": "koi-pond"}, headers=user_headers)
        assert r.status_code == 403


def test_rueckfrage_und_unbekannt(client, admin_headers, env):
    r = client.post(B + "/devices/t1/addons/install", json={"addon": "koi-pond"}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_confirm_required"
    r = client.post(B + "/devices/t1/addons/install", json={"confirm": True, "addon": "../x"}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_addon_unknown"
    assert client.get(B + "/addons/..%2Fx/image", headers=admin_headers).status_code == 404


def test_zustand_ohne_katalog(client, admin_headers, env):
    r = client.get(B + "/devices/t1/addons", headers=admin_headers)
    assert r.status_code == 200 and r.json()["items"] is None and r.json()["job"] is None
