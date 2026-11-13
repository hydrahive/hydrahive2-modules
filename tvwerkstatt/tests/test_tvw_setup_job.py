"""Baustein 3: Auftrag „Werkstatt einrichten“ – Ablauf, Fehler mit Schritt, Neustart, Schnittstellen."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, jobs, network, provision

B = "/api/modules/tvwerkstatt"


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(fake_incus, db_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(provision, "_PAUSES", (0.0, 0.0))
    monkeypatch.setattr(provision, "keystore_path", lambda: tmp_path / "k" / "debug.keystore")
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _job() -> dict:
    return jobs.last_setup() or {}


def test_einrichten_ganz(env):
    job_id = jobs.begin_setup("boss", license_accepted=True)
    run(jobs.run_setup(job_id))
    j = _job()
    assert (j["state"], j["step"], j["error_code"]) == ("done", "done", "")
    assert env.containers["hh-tvwerkstatt"]["running"] is False             # nach dem Einrichten angehalten
    assert env.networks["hhtvw0"]["security.acls"] == "hhtvw-acl"
    assert not jobs.busy()


def test_ohne_lizenz_kein_auftrag(env):
    with pytest.raises(jobs.JobError) as e:
        jobs.begin_setup("boss", license_accepted=False)
    assert e.value.code == "tvw_license_required" and jobs.last_setup() is None


def test_nur_ein_auftrag_gleichzeitig(env):
    jobs.begin_setup("boss", license_accepted=True)
    with pytest.raises(jobs.JobError) as e:
        jobs.begin_setup("boss", license_accepted=True)
    assert e.value.code == "tvw_busy"


def test_fehler_mit_schritt_und_ausgabe(env):
    env.exec_answers["apt-get update"] = (1, "E: Unable to locate package")
    run_id = jobs.begin_setup("boss", license_accepted=True)
    with pytest.raises(jobs.JobError):
        run(jobs.run_setup(run_id))
    j = _job()
    assert (j["state"], j["step"], j["error_code"]) == ("failed", "packages", "tvw_setup_failed")
    assert "Unable to locate package" in j["error_detail"]
    assert jobs.retry_step() == "packages"


def test_netz_offen_bricht_ab_und_meldet(env):
    env.open_targets.add("192.168.178.2:22")
    run_id = jobs.begin_setup("boss", license_accepted=True)
    with pytest.raises(jobs.JobError):
        run(jobs.run_setup(run_id))
    assert (_job()["step"], _job()["error_code"]) == ("probe", "tvw_net_open")
    assert jobs.retry_step() == ""                                         # Probe ist kein Einrichtungsschritt


def test_unterbrochen_nach_neustart(env):
    jobs.begin_setup("boss", license_accepted=True)
    jobs.reset()                                                           # wie ein Neustart des Servers
    j = _job()
    assert (j["state"], j["error_code"]) == ("failed", "tvw_interrupted")


def test_fernseher_kommen_in_die_sperrliste(env):
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, created_by) "
                     "VALUES ('d1', 'Wohnzimmer', '192.168.178.200', 'boss')")
        conn.commit()
    run(jobs.run_setup(jobs.begin_setup("boss", license_accepted=True)))
    dests = [r.get("destination") for r in env.acls["hhtvw-acl"]["egress"]]
    assert "192.168.178.200/32" in dests


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_einrichten_nur_admins(client, user_headers, env):
    assert client.post(B + "/setup", json={"accept_license": True}, headers=user_headers).status_code == 403
    assert client.post(B + "/container/stop", json={}, headers=user_headers).status_code == 403
    assert client.delete(B + "/container", headers=user_headers).status_code == 403


def test_einrichten_ohne_lizenz_400(client, admin_headers, env):
    r = client.post(B + "/setup", json={}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_license_required"


def test_einrichten_startet_und_zustand_zeigt_es(client, admin_headers, env):
    r = client.post(B + "/setup", json={"accept_license": True}, headers=admin_headers)
    assert r.status_code == 202 and r.json()["job_id"]
    d = client.get(B + "/state", headers=admin_headers).json()
    assert d["setup"]["job_id"] == r.json()["job_id"]
    assert d["container"] in ("missing", "running", "stopped")
    assert "target" not in d["setup"]


def test_zustand_ohne_incus(client, admin_headers, monkeypatch):
    from backend import incus
    monkeypatch.setattr(incus, "available", lambda: False)
    d = client.get(B + "/state", headers=admin_headers).json()
    assert d["incus"] is False and d["setup"] is None and d["container"] == "missing"


def test_anhalten_waehrend_einrichtung_409(client, admin_headers, env):
    jobs.begin_setup("boss", license_accepted=True)
    r = client.post(B + "/container/stop", json={}, headers=admin_headers)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "tvw_busy"


def test_abbauen(client, admin_headers, env):
    env.containers["hh-tvwerkstatt"] = {"running": True, "network": "hhtvw0"}
    r = client.delete(B + "/container", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"container": "missing"}


def test_nochmal_nach_abbau_beginnt_von_vorn(env):
    """Fund beim Bau: Nach einem Fehler bei „sdk“ und anschließendem Abbauen fehlen Java und Werkzeuge. „Nochmal“ darf
    dann nicht bei „sdk“ weitermachen, sondern muss alles neu einrichten."""
    run(jobs.run_setup(jobs.begin_setup("boss", license_accepted=True), start_at="sdk"))
    assert "hh-tvwerkstatt" in env.containers
    env.containers.pop("hh-tvwerkstatt")
    env.exec_log.clear()
    run(jobs.run_setup(jobs.begin_setup("boss", license_accepted=True), start_at="sdk"))
    assert any("apt-get install" in b for b in env.exec_log)
