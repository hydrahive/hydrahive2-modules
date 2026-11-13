"""Entrümpeln Teil 1: Auftrag „Vom Fernseher lesen“ und Schnittstellen. incus-Attrappe, erfundene Listen."""
from __future__ import annotations

import asyncio
import base64
import io
import json
import tarfile

import pytest
from backend import container, debloat_jobs, jobs, network, source

B = "/api/modules/tvwerkstatt"
GTV = "com.google.android.apps.tv.launcherx"
LIST = """# TCL Beispiel (G08_4K_GB, G08), firmware UTT2.250416.001 AU02
#
# Left enabled on purpose: com.tcl.ttvs (firmware updater).

# TCL pushes
com.tcl.dashboard   # promos
com.tcl.logkit      # log capture
"""
READ = ("__TVW__ state=device\n__TVW__ brand=TCL\n__TVW__ product=G08_4K_GB\n__TVW__ device=G08\n"
        "__TVW__ model=Smart TV Pro\n__TVW__ build_id=UTT2.250416.001\n__TVW__ incremental=AU02\n"
        "__TVW__ all com.tcl.dashboard\n__TVW__ all com.tcl.logkit\n__TVW__ all com.tcl.ttvs\n"
        "__TVW__ all com.netflix.ninja\n"
        "__TVW__ off com.tcl.logkit\n")


def tar_b64(files: dict[str, str]) -> str:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name, text in files.items():
            data = text.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
    return base64.b64encode(buf.getvalue()).decode()


LISTS = tar_b64({"./tcl-a/debloat.txt": LIST, "./tcl-a/tv.json": json.dumps({"brand": "TCL"}),
                 "./tcl-a/README.md": "nicht gelesen", "./evil/debloat.txt": "x" * 300_000})


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(fake_incus, db_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(debloat_jobs, "_cache", lambda commit: tmp_path / f"lists-{commit[:12]}.json")
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, sdk, kind, stock_home, "
                     "current_home, created_by) VALUES ('t1', 'Wohnzimmer', '192.168.178.201', 34, 'google_tv', ?, ?, "
                     "'boss')", (GTV, GTV))
        conn.commit()
    a = fake_incus.exec_answers
    a["git fetch"] = (0, "")
    a["debloat*.txt"] = (0, LISTS + "\n")
    a["pm list packages"] = (0, READ)
    jobs.reset()
    yield fake_incus
    jobs.reset()


def _go() -> dict:
    job_id = jobs.begin("debloat_read", "t1", "boss", "container")
    run(debloat_jobs.run_read(job_id, "t1"))
    return jobs.last_job("debloat_read", "t1")


def test_lesen_und_ansicht(env):
    j = _go()
    assert (j["state"], j["error_code"]) == ("done", "")
    v = debloat_jobs.view("t1", GTV)
    rows = {r["package"]: r for r in v["packages"]}
    assert v["lists_used"] == ["tcl-a/debloat.txt"] and v["commit_id"] == source.COMMIT[:7]
    assert rows["com.tcl.dashboard"]["state"] == "on" and rows["com.tcl.logkit"]["state"] == "off"
    assert "com.tcl.ttvs" not in rows and "com.netflix.ninja" not in rows
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_nur_lesende_befehle_am_fernseher(env):
    _go()
    tv = " ".join(b for b in env.exec_log if "adb" in b)
    for verb in ("disable", "enable", "uninstall", "install ", "settings put", "set-home", "am start"):
        assert verb not in tv, verb


def test_listen_nur_einmal_je_stand(env):
    _go()
    _go()
    assert sum("debloat*.txt" in b for b in env.exec_log) == 1


def test_zu_grosse_und_fremde_dateien_werden_nicht_gelesen(env):
    _go()
    lists = debloat_jobs.load_lists()
    assert list(lists) == ["tcl-a/debloat.txt"]


def test_fernseher_antwortet_nicht(env):
    env.exec_answers["pm list packages"] = (0, "__TVW__ state=offline\n")
    j = _go()
    assert (j["state"], j["error_code"]) == ("failed", "tvw_adb_closed")
    assert debloat_jobs.view("t1", GTV) is None


def test_kaputtes_archiv(env):
    env.exec_answers["debloat*.txt"] = (0, "A" * 200 + "\n")
    assert _go()["error_code"] == "tvw_debloat_lists_failed"


def test_leere_paketliste(env):
    env.exec_answers["pm list packages"] = (0, "__TVW__ state=device\n__TVW__ brand=TCL\n")
    assert _go()["error_code"] == "tvw_debloat_read_failed"


# --- Schnittstellen -------------------------------------------------------------------------------------------

def test_nur_admins(client, user_headers, env):
    assert client.get(B + "/devices/t1/debloat", headers=user_headers).status_code == 403
    assert client.post(B + "/devices/t1/debloat/read", json={}, headers=user_headers).status_code == 403


def test_zustand_vor_dem_lesen(client, admin_headers, env):
    r = client.get(B + "/devices/t1/debloat", headers=admin_headers)
    assert r.status_code == 200 and r.json() == {"view": None, "read_job": None, "switch_job": None, "backup_at": ""}


def test_lesen_starten(client, admin_headers, env):
    r = client.post(B + "/devices/t1/debloat/read", json={}, headers=admin_headers)
    assert r.status_code == 202
    assert client.get(B + "/devices/t1/debloat", headers=admin_headers).json()["read_job"]["job_id"] == r.json()["job_id"]


def test_unbekanntes_geraet(client, admin_headers, env):
    assert client.get(B + "/devices/nix/debloat", headers=admin_headers).status_code == 404
    assert client.post(B + "/devices/nix/debloat/read", json={}, headers=admin_headers).status_code == 404
