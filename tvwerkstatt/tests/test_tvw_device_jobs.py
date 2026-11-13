"""Baustein 5: Fernseher eintragen, prüfen (Auftrag), entfernen – mit incus-Attrappe, ohne echten Fernseher."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, device_jobs, jobs, network, provision

B = "/api/modules/tvwerkstatt"
ADDR = "192.168.178.200"
OK = ("__TVW__ state=device\n__TVW__ ro.product.model=BRAVIA 4K UR3\n__TVW__ ro.product.manufacturer=Sony\n"
      "__TVW__ ro.build.version.release=9\n__TVW__ ro.build.version.sdk=28\n__TVW__ ro.build.display.id=PTT1\n"
      "__TVW__ home=com.gathin.tvhome\n__TVW__ has_stock_tv=package:\n")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(fake_incus, db_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(device_jobs, "_STEP_S", 0)
    monkeypatch.setattr(provision, "adbkey_dir", lambda: tmp_path / "adb")
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    fake_incus.exec_answers["__TVW__"] = (0, OK)
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _check(device_id: str) -> dict:
    job_id = jobs.begin("probe", device_id, "boss", "network")
    run(device_jobs.run_check(job_id, device_id))
    return jobs.last_job("probe", device_id)


def _dev(device_id: str) -> dict:
    return next(d for d in device_jobs.state.devices() if d["device_id"] == device_id)


def test_eintragen_und_pruefen(env):
    did = device_jobs.add("Wohnzimmer", ADDR, 5555, "boss")
    j = _check(did)
    assert (j["state"], j["error_code"]) == ("done", "")
    d = _dev(did)
    assert (d["model"], d["android"], d["sdk"], d["adb_state"]) == ("Sony BRAVIA 4K UR3", "9", 28, "open")
    assert (d["stock_home"], d["current_home"], d["kind"]) == ("com.google.android.tvlauncher", "com.gathin.tvhome",
                                                               "android_tv")
    assert d["checked_at"]
    assert env.containers["hh-tvwerkstatt"]["running"] is False                  # danach wieder angehalten
    assert f"{ADDR}/32" in [r.get("destination") for r in env.acls["hhtvw-acl"]["egress"]]


def test_pruefen_schaltet_nichts_am_fernseher(env):
    _check(device_jobs.add("Wohnzimmer", ADDR, 5555, "boss"))
    alles = " ".join(env.exec_log)
    for verboten in ("pm disable", "pm install", "set-home-activity", "settings put", "reboot", "tcpip"):
        assert verboten not in alles


def test_adb_schluessel_wird_gesichert(env):
    _check(device_jobs.add("Wohnzimmer", ADDR, 5555, "boss"))
    pulls = [c for c in env.calls if c[:2] == ["file", "pull"]]
    assert [c[2] for c in pulls] == ["hh-tvwerkstatt/home/ubuntu/.android/adbkey",
                                     "hh-tvwerkstatt/home/ubuntu/.android/adbkey.pub"]


def test_freigabe_fehlt_nach_wartezeit(env, monkeypatch):
    monkeypatch.setattr(device_jobs, "WAIT_AUTH_S", 0.0)
    env.exec_answers["__TVW__"] = (0, "__TVW__ state=unauthorized\n")
    did = device_jobs.add("Wohnzimmer", ADDR, 5555, "boss")
    j = _check(did)
    assert (j["state"], j["error_code"], j["step"]) == ("failed", "tvw_adb_unauthorized", "connect")
    assert _dev(did)["adb_state"] == "unauthorized"


def test_wartet_auf_freigabe_und_macht_dann_weiter(env, monkeypatch):
    antworten = iter([(0, "__TVW__ state=unauthorized\n"), (0, "__TVW__ state=unauthorized\n"), (0, OK)])
    real = env._exec

    def nacheinander(a):
        if "__TVW__" in " ".join(a):
            rc, out = next(antworten)
            return rc, out, ""
        return real(a)
    monkeypatch.setattr(env, "_exec", nacheinander)
    did = device_jobs.add("Wohnzimmer", ADDR, 5555, "boss")
    assert _check(did)["state"] == "done"


def test_debugging_zu(env):
    env.exec_answers["__TVW__"] = (0, "__TVW__ state=error: device not found\n")
    did = device_jobs.add("Wohnzimmer", ADDR, 5555, "boss")
    assert _check(did)["error_code"] == "tvw_adb_closed"
    assert _dev(did)["adb_state"] == "closed"


def test_zu_altes_android(env):
    env.exec_answers["__TVW__"] = (0, OK.replace("sdk=28", "sdk=25"))
    assert _check(device_jobs.add("Alt", ADDR, 5555, "boss"))["error_code"] == "tvw_sdk_too_old"


def test_ohne_eingerichtete_werkstatt(env):
    env.containers.pop("hh-tvwerkstatt")
    assert _check(device_jobs.add("Wohnzimmer", ADDR, 5555, "boss"))["error_code"] == "tvw_not_set_up"


def test_adresse_doppelt(env):
    device_jobs.add("Wohnzimmer", ADDR, 5555, "boss")
    with pytest.raises(device_jobs.device.TvwDeviceError) as e:
        device_jobs.add("Nochmal", ADDR, 5555, "boss")
    assert e.value.code == "tvw_device_exists"


def test_entfernen_nimmt_ausnahme_aus_der_sperrliste(env):
    did = device_jobs.add("Wohnzimmer", ADDR, 5555, "boss")
    _check(did)
    run(device_jobs.remove(did))
    assert device_jobs.state.devices() == []
    assert f"{ADDR}/32" not in [r.get("destination") for r in env.acls["hhtvw-acl"]["egress"]]


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_nur_admins(client, user_headers, env):
    assert client.post(B + "/devices", json={"name": "x", "address": ADDR}, headers=user_headers).status_code == 403
    assert client.delete(B + "/devices/abc", headers=user_headers).status_code == 403


def test_eintragen_ueber_schnittstelle(client, admin_headers, env):
    r = client.post(B + "/devices", json={"name": "Wohnzimmer", "address": ADDR}, headers=admin_headers)
    assert r.status_code == 202 and r.json()["device_id"] and r.json()["job_id"]
    d = client.get(B + "/state", headers=admin_headers).json()["devices"][0]
    assert d["name"] == "Wohnzimmer" and d["check"]["job_id"] == r.json()["job_id"]


@pytest.mark.parametrize("addr", ["8.8.8.8", "192.168.178.2", "kein.fernseher"])
def test_schnittstelle_lehnt_falsche_adresse_ab(client, admin_headers, env, addr):
    r = client.post(B + "/devices", json={"name": "x", "address": addr}, headers=admin_headers)
    assert r.status_code in (400, 422)
    assert client.get(B + "/state", headers=admin_headers).json()["devices"] == []


def test_schnittstelle_ohne_werkstatt(client, admin_headers, env):
    env.containers.pop("hh-tvwerkstatt")
    r = client.post(B + "/devices", json={"name": "x", "address": ADDR}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "tvw_not_set_up"


def test_unbekanntes_geraet(client, admin_headers, env):
    assert client.post(B + "/devices/gibtsnicht/check", json={}, headers=admin_headers).status_code == 404
    assert client.delete(B + "/devices/gibtsnicht", headers=admin_headers).status_code == 404
