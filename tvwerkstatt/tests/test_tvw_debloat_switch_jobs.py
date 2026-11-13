"""Entrümpeln Teil 2: Aufträge Ab-/Einschalten mit incus-Attrappe, Schnittstellen. Ohne echten Fernseher."""
from __future__ import annotations

import asyncio

import pytest
from backend import container, debloat_switch_jobs, jobs, network

B = "/api/modules/tvwerkstatt"
GTV = "com.google.android.apps.tv.launcherx"
OK = "__TVW__ state=device\n"
HOME = "__TVW__ home=com.gathin.tvhome/.MainActivity\n"
READ = (OK + "__TVW__ brand=TCL\n__TVW__ all com.tcl.logkit\n__TVW__ all com.tcl.exhibit\n__TVW__ all com.tcl.guard\n"
        "__TVW__ all com.tcl.messagebox\n__TVW__ all com.tcl.esticker\n")
GUARD = (OK + "__TVW__ hw com.tcl.logkit ok\n__TVW__ hw com.tcl.exhibit ok\n__TVW__ hw com.tcl.guard ok\n"
         "__TVW__ hw com.tcl.messagebox ok\n__TVW__ hw com.tcl.esticker ok\n__TVW__ hw com.tcl.tvinput hw\n" + HOME)
FIVE = ["com.tcl.logkit", "com.tcl.exhibit", "com.tcl.guard", "com.tcl.messagebox", "com.tcl.esticker"]


def run(coro):
    return asyncio.run(coro)


def offs(pkgs: list[str], home: str = HOME) -> tuple[int, str]:
    return 0, OK + "".join(f"__TVW__ off {p}\n" for p in pkgs) + home


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
    a["pm list packages | tr"] = (0, READ)
    a["TV_INPUT_HARDWARE"] = (0, GUARD)
    a["pm disable-user"] = offs(FIVE)
    a["pm enable --user 0"] = offs([])
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _go(pkgs: list[str] | None, on: bool = False) -> dict:
    kind = "debloat_on" if on else "debloat_off"
    pk = debloat_switch_jobs.prepare("t1", pkgs, on=on)
    job_id = jobs.begin(kind, "t1", "boss", "container")
    run(debloat_switch_jobs.run_switch(job_id, "t1", pk, on))
    return jobs.last_job(kind, "t1")


def _calls(env, needle: str) -> list[str]:
    return [b for b in env.exec_log if needle in b]


def test_abschalten_in_schueben_mit_sicherung_und_vermerk(env):
    j = _go(FIVE)
    assert (j["state"], j["error_code"]) == ("done", "")
    assert len(_calls(env, "pm disable-user")) == 2                       # 4 + 1
    assert debloat_switch_jobs.ours("t1") == sorted(FIVE) or set(debloat_switch_jobs.ours("t1")) == set(FIVE)
    assert debloat_switch_jobs.backup_of("t1")["packages"]["com.tcl.logkit"] == "on"
    first = next(i for i, b in enumerate(env.exec_log) if "TV_INPUT_HARDWARE" in b)
    assert first < next(i for i, b in enumerate(env.exec_log) if "pm disable-user" in b)
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_gesperrt_am_geraet_nichts_wird_geaendert(env):
    j = _go(["com.tcl.logkit", "com.tcl.tvinput"])
    assert (j["error_code"], j["error_detail"]) == ("tvw_debloat_blocked", "com.tcl.tvinput: inputs")
    assert not _calls(env, "pm disable-user") and debloat_switch_jobs.ours("t1") == []


def test_home_springt_alles_aus_dem_auftrag_wieder_an(env):
    env.exec_answers["pm disable-user"] = offs(FIVE[:4], "__TVW__ home=com.android.tv.settings/.FallbackHome\n")
    j = _go(FIVE)
    assert j["error_code"] == "tvw_debloat_home_changed"
    on = _calls(env, "pm enable --user 0")
    assert on and all(f"pm enable --user 0 {p}" in on[0] for p in FIVE[:4])
    assert len(_calls(env, "pm disable-user")) == 1 and debloat_switch_jobs.ours("t1") == []


def test_paket_geht_nicht_aus_rueckweg(env):
    env.exec_answers["pm disable-user"] = offs(FIVE[:3])
    assert _go(FIVE[:4])["error_code"] == "tvw_debloat_not_off"
    assert debloat_switch_jobs.ours("t1") == []


def test_rueckweg_scheitert_ehrlich_vermerk_bleibt(env):
    env.exec_answers["pm disable-user"] = offs(FIVE[:4], "__TVW__ home=android\n")
    env.exec_answers["pm enable --user 0"] = offs(FIVE[:4])
    assert _go(FIVE[:4])["error_code"] == "tvw_debloat_restore_incomplete"
    assert set(debloat_switch_jobs.ours("t1")) == set(FIVE[:4])


def test_alles_zurueck_nur_was_die_werkstatt_abgeschaltet_hat(env):
    _go(FIVE[:2])
    j = _go(None, on=True)
    assert (j["state"], j["error_code"]) == ("done", "")
    on = " ".join(_calls(env, "pm enable --user 0"))
    assert "com.tcl.logkit" in on and "com.tcl.exhibit" in on and "com.tcl.guard" not in on
    assert debloat_switch_jobs.ours("t1") == []


def test_einschalten_klappt_nicht_vermerk_bleibt(env):
    _go(FIVE[:1])
    env.exec_answers["pm enable --user 0"] = offs(FIVE[:1])
    assert _go(None, on=True)["error_code"] == "tvw_debloat_not_on"
    assert debloat_switch_jobs.ours("t1") == ["com.tcl.logkit"]


def test_alles_zurueck_ohne_vermerke(env):
    from backend import debloat_switch
    with pytest.raises(debloat_switch.TvwDebloatError) as e:
        debloat_switch_jobs.prepare("t1", None, on=True)
    assert e.value.code == "tvw_debloat_nothing"


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_nur_admins(client, user_headers, env):
    for path in ("/devices/t1/debloat/off", "/devices/t1/debloat/on"):
        assert client.post(B + path, json={"confirm": True, "packages": FIVE}, headers=user_headers).status_code == 403


@pytest.mark.parametrize("path", ["/devices/t1/debloat/off", "/devices/t1/debloat/on"])
def test_ohne_rueckfrage_nichts(client, admin_headers, env, path):
    r = client.post(B + path, json={"packages": FIVE}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_confirm_required"


def test_gesperrtes_schon_an_der_schnittstelle_abgelehnt(client, admin_headers, env):
    r = client.post(B + "/devices/t1/debloat/off", json={"confirm": True, "packages": [GTV]}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_debloat_locked"
    r = client.post(B + "/devices/t1/debloat/off", json={"confirm": True}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_debloat_bad_package"


def test_abschalten_startet_und_zustand_zeigt_es(client, admin_headers, env):
    r = client.post(B + "/devices/t1/debloat/off", json={"confirm": True, "packages": FIVE[:2]}, headers=admin_headers)
    assert r.status_code == 202
    d = client.get(B + "/devices/t1/debloat", headers=admin_headers).json()
    assert d["switch_job"]["job_id"] == r.json()["job_id"]
