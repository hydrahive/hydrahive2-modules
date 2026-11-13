"""E2: Schnittstellen und Aufträge Desktop – Aussehen speichern, Apps lesen, Hintergründe, Aussehen schieben."""
from __future__ import annotations

import asyncio
import io

import pytest
from backend import apps, container, jobs, look_jobs, network, provision, wallpapers

B = "/api/modules/tvwerkstatt"
LIST = "__TVW__ state=device\n__TVW__ pkg com.netflix.ninja 50157\n__TVW__ pkg com.gathin.tvhome 13\n"


def run(coro):
    return asyncio.run(coro)


def _jpeg(w=3000, h=2000, color=(30, 60, 90)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def env(fake_incus, db_ready, monkeypatch, tmp_path):
    monkeypatch.setattr(container, "_WAIT_STEP", 0)
    monkeypatch.setattr(network, "_host_networks", lambda: set())
    monkeypatch.setattr(network, "_host_addresses", lambda: {"192.168.178.2/32"})
    monkeypatch.setattr(wallpapers, "folder", lambda d: tmp_path / "w" / d)
    monkeypatch.setattr(apps, "image_dir", lambda d: tmp_path / "a" / d)
    monkeypatch.setattr(provision, "keystore_path", lambda: tmp_path / "k")
    run(network.ensure_network([]))
    fake_incus.containers["hh-tvwerkstatt"] = {"running": False, "network": "hhtvw0"}
    from hydrahive.db.connection import db
    with db() as conn:
        conn.execute("INSERT INTO module_tvwerkstatt_devices (device_id, name, address, created_by) "
                     "VALUES ('d1', 'Wohnzimmer', '192.168.178.200', 'boss')")
        conn.commit()
    fake_incus.exec_answers["query-activities"] = (0, LIST)
    fake_incus.exec_answers["tvw-app.apk"] = (0, "__TVW__ app\tcom.netflix.ninja\tbanner\tNetflix\n")
    fake_incus.exec_answers["content://com.gathin.tvhome.theme"] = (0, "__TVW__ state=device\n__TVW__ restarted\n")
    jobs.reset()
    yield fake_incus
    jobs.reset()


def test_desktop_leer(client, admin_headers, env):
    d = client.get(B + "/devices/d1/desktop", headers=admin_headers).json()
    assert d["look"]["columns"] == 6 and d["apps"] == [] and d["wallpapers"] == []
    assert d["pushed_current"] is False and d["read_job"] is None


def test_aussehen_speichern_und_pruefen(client, admin_headers, env):
    r = client.put(B + "/devices/d1/look", json={"columns": 4, "dock": ["com.netflix.ninja"]}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["look"]["columns"] == 4
    assert client.get(B + "/devices/d1/desktop", headers=admin_headers).json()["look"]["dock"] == ["com.netflix.ninja"]
    r = client.put(B + "/devices/d1/look", json={"columns": 12}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"] == {"code": "tvw_look_invalid", "params": {"field": "columns"}}


def test_nur_admins(client, user_headers, env):
    assert client.get(B + "/devices/d1/desktop", headers=user_headers).status_code == 403
    assert client.put(B + "/devices/d1/look", json={}, headers=user_headers).status_code == 403
    assert client.post(B + "/devices/d1/look/push", json={"confirm": True}, headers=user_headers).status_code == 403


def test_unbekanntes_geraet(client, admin_headers, env):
    assert client.get(B + "/devices/nix/desktop", headers=admin_headers).status_code == 404


def test_apps_lesen(env):
    job_id = jobs.begin("apps", "d1", "boss", "container")
    run(look_jobs.run_read_apps(job_id, "d1"))
    assert jobs.last_job("apps", "d1")["state"] == "done"
    got = look_jobs.known_apps("d1")
    assert [(a["package"], a["label"], a["has_banner"]) for a in got] == [("com.netflix.ninja", "Netflix", 1)]
    assert env.containers["hh-tvwerkstatt"]["running"] is False


def test_apps_zweites_lesen_zieht_nur_neues(env):
    for _ in range(2):
        run(look_jobs.run_read_apps(jobs.begin("apps", "d1", "boss", "container"), "d1"))
    assert sum("tvw-app.apk" in b for b in env.exec_log) == 1


def test_hintergrund_hochladen_wird_verkleinert(client, admin_headers, env):
    r = client.post(B + "/devices/d1/wallpapers", data={"mood": "night"}, headers=admin_headers,
                    files={"file": ("strand.jpg", _jpeg(), "image/jpeg")})
    assert r.status_code == 200, r.text
    w = r.json()["wallpaper"]
    assert w["mood"] == "night" and w["file_name"].startswith("night-") and w["title"] == "strand.jpg"
    img = client.get(B + f"/devices/d1/wallpapers/{w['wallpaper_id']}/image", headers=admin_headers)
    from PIL import Image
    with Image.open(io.BytesIO(img.content)) as im:
        assert im.size == (1920, 1080)
    assert len(img.content) <= wallpapers.TARGET


@pytest.mark.parametrize("data,code", [(b"kein bild", "tvw_image_invalid"), (b"", "tvw_image_invalid")])
def test_hintergrund_kaputt(client, admin_headers, env, data, code):
    r = client.post(B + "/devices/d1/wallpapers", data={"mood": "night"}, headers=admin_headers,
                    files={"file": ("x.jpg", data, "image/jpeg")})
    assert r.status_code == 400 and r.json()["detail"]["code"] == code


def test_hintergrund_falsche_tageszeit(client, admin_headers, env):
    r = client.post(B + "/devices/d1/wallpapers", data={"mood": "mittag"}, headers=admin_headers,
                    files={"file": ("x.jpg", _jpeg(400, 300), "image/jpeg")})
    assert r.status_code == 400


def test_hintergrund_loeschen(client, admin_headers, env):
    w = client.post(B + "/devices/d1/wallpapers", data={"mood": "morning"}, headers=admin_headers,
                    files={"file": ("x.jpg", _jpeg(400, 300), "image/jpeg")}).json()["wallpaper"]
    assert client.delete(B + f"/devices/d1/wallpapers/{w['wallpaper_id']}", headers=admin_headers).status_code == 200
    assert wallpapers.list_for("d1") == []


def test_schieben_nur_mit_rueckfrage(client, admin_headers, env):
    r = client.post(B + "/devices/d1/look/push", json={}, headers=admin_headers)
    assert r.status_code == 400 and r.json()["detail"]["code"] == "tvw_confirm_required"


def test_schieben_ganz_und_stand_aktuell(client, admin_headers, env):
    client.post(B + "/devices/d1/wallpapers", data={"mood": "evening"}, headers=admin_headers,
                files={"file": ("x.jpg", _jpeg(400, 300), "image/jpeg")})
    job_id = jobs.begin("look", "d1", "boss", "container")
    run(look_jobs.run_push_look(job_id, "d1"))
    assert jobs.last_job("look", "d1")["state"] == "done"
    staged = [c for c in env.calls if c[0] == "exec" and "tar -x -C /home/ubuntu/theme" in " ".join(c)]
    assert staged
    d = client.get(B + "/devices/d1/desktop", headers=admin_headers).json()
    assert d["pushed_current"] is True and d["pushed_at"]
    client.put(B + "/devices/d1/look", json={"columns": 3}, headers=admin_headers)
    assert client.get(B + "/devices/d1/desktop", headers=admin_headers).json()["pushed_current"] is False


def test_schieben_datei_fehlt(env):
    env.exec_answers["content://com.gathin.tvhome.theme"] = (0, "__TVW__ state=device\ntvw-not-written config.json\n")
    run(look_jobs.run_push_look(jobs.begin("look", "d1", "boss", "container"), "d1"))
    j = jobs.last_job("look", "d1")
    assert (j["state"], j["error_code"]) == ("failed", "tvw_look_push_failed")


def test_schieben_ohne_freigabe(env):
    env.exec_answers["content://com.gathin.tvhome.theme"] = (0, "__TVW__ state=unauthorized\n")
    run(look_jobs.run_push_look(jobs.begin("look", "d1", "boss", "container"), "d1"))
    assert jobs.last_job("look", "d1")["error_code"] == "tvw_adb_unauthorized"
