"""Routen „Sender“ (PLAN-E2.md Punkt 6, „Rechte“): sehen alle mit module.radiostream, steuern nur radiostream.control.

control wird durch `fake_control` ersetzt – hier geht es um Rechte, Antworten und Fehlercodes, nicht um systemd.
"""
from __future__ import annotations

import pytest

P = "/api/modules/radiostream"


@pytest.fixture
def fake_control(monkeypatch):
    from backend import control
    calls: list[str] = []
    state = {"running": False, "fail": None}

    def act(name):
        def _f():
            calls.append(name)
            if state["fail"]:
                raise control.ControlError(state["fail"])
            if name == "start":
                state["running"] = True
            if name == "stop":
                state["running"] = False
        return _f

    for name in ("start", "stop", "skip", "apply_listener_site"):
        monkeypatch.setattr(control, name, act(name))
    monkeypatch.setattr(control, "status", lambda: {"installed": True, "running": state["running"]})
    monkeypatch.setattr(control, "now_playing", lambda: {"artist": "Künstler", "title": "Titel"})
    monkeypatch.setattr(control, "listeners", lambda: 3)
    return {"calls": calls, "state": state}


def test_status_sehen_alle_mit_modul(client, user_headers, fake_control, db_ready):
    r = client.get(f"{P}/station", headers=user_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["running"] is False and d["installed"] is True
    assert d["now"] == {"artist": "Künstler", "title": "Titel"} and d["listeners"] == 3
    assert d["settings"]["name"] == "Radiostream" and d["settings"]["listen_port"] == 8800
    assert isinstance(d["recent"], list) and "can_control" in d


def test_status_sagt_ob_man_steuern_darf(client, user_headers, admin_headers, fake_control, db_ready):
    assert client.get(f"{P}/station", headers=user_headers).json()["can_control"] is False
    assert client.get(f"{P}/station", headers=admin_headers).json()["can_control"] is True


def test_status_ohne_anmeldung_401(client, fake_control, db_ready):
    assert client.get(f"{P}/station").status_code == 401


def test_keine_geheimnisse_im_status(client, admin_headers, fake_control, db_ready, tmp_path, monkeypatch):
    from backend import feed_auth
    f = tmp_path / "s.env"
    f.write_text("RADIOSTREAM_SOURCE_PASSWORD=GEHEIM-Q\nRADIOSTREAM_ADMIN_PASSWORD=GEHEIM-A\nRADIOSTREAM_FEED_KEY=GEHEIM-F\n")
    monkeypatch.setattr(feed_auth, "SECRETS_FILE", f)
    assert "GEHEIM" not in client.get(f"{P}/station", headers=admin_headers).text


@pytest.mark.parametrize("path", ["/station/start", "/station/stop", "/station/skip"])
def test_steuern_nur_mit_freigabe(client, user_headers, fake_control, db_ready, path):
    r = client.post(f"{P}{path}", headers=user_headers)
    assert r.status_code == 403
    assert fake_control["calls"] == []


@pytest.mark.parametrize("path, call", [("/station/start", "start"), ("/station/stop", "stop"),
                                        ("/station/skip", "skip")])
def test_admin_steuert(client, admin_headers, fake_control, db_ready, path, call):
    r = client.post(f"{P}{path}", headers=admin_headers)
    assert r.status_code == 200, r.text
    assert fake_control["calls"] == [call]
    assert "running" in r.json()


@pytest.mark.parametrize("code, http", [("radiostream_service_missing", 409), ("radiostream_service_failed", 502),
                                        ("radiostream_not_running", 409), ("radiostream_nginx_failed", 502),
                                        ("radiostream_port_in_use", 409)])
def test_fehler_kommen_als_code(client, admin_headers, fake_control, db_ready, code, http):
    fake_control["state"]["fail"] = code
    r = client.post(f"{P}/station/start", headers=admin_headers)
    assert r.status_code == http
    assert code in r.text


def test_einstellungen_speichern_nur_admin(client, user_headers, fake_control, db_ready):
    r = client.put(f"{P}/station/settings", headers=user_headers, json={"name": "X"})
    assert r.status_code == 403


def test_einstellungen_speichern_und_zurueck(client, admin_headers, fake_control, db_ready):
    r = client.put(f"{P}/station/settings", headers=admin_headers,
                   json={"name": "Molke FM", "max_listeners": 20, "reach": "home"})
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["name"] == "Molke FM" and r.json()["settings"]["reach"] == "home"
    assert fake_control["calls"] == []          # Sender aus → nichts neu anwenden


def test_einstellungen_bei_laufendem_sender_neu_anwenden(client, admin_headers, fake_control, db_ready):
    fake_control["state"]["running"] = True
    r = client.put(f"{P}/station/settings", headers=admin_headers, json={"name": "Neu"})
    assert r.status_code == 200
    assert fake_control["calls"] == ["start"]   # start schreibt Konfiguration + Hörer-Seite neu


@pytest.mark.parametrize("body, code", [({"listen_port": 8001}, "radiostream_port_invalid"),
                                        ({"listen_port": 80}, "radiostream_port_invalid"),
                                        ({"reach": "welt"}, "radiostream_station_invalid"),
                                        ({"max_listeners": 0}, "radiostream_station_invalid"),
                                        ({"name": "   "}, "radiostream_station_invalid")])
def test_einstellungen_ungueltig(client, admin_headers, fake_control, db_ready, body, code):
    r = client.put(f"{P}/station/settings", headers=admin_headers, json=body)
    assert r.status_code == 400 and code in r.text


def test_unbekanntes_feld_abgelehnt(client, admin_headers, fake_control, db_ready):
    r = client.put(f"{P}/station/settings", headers=admin_headers, json={"updated_by": "jemand"})
    assert r.status_code in (400, 422)


def test_status_verbraucht_keinen_titel(client, user_headers, fake_control, db_ready):
    """Status zeigt „zuletzt gespielt“, wählt aber nie einen Titel aus (sonst sperrt jede Ansicht Künstler)."""
    from backend import rotation
    rotation.record("t_x", "Künstler X", album_artist="")
    from hydrahive.db.connection import db
    with db() as conn:
        before = conn.execute("SELECT COUNT(*) FROM module_radiostream_plays").fetchone()[0]
    d = client.get(f"{P}/station", headers=user_headers).json()
    with db() as conn:
        after = conn.execute("SELECT COUNT(*) FROM module_radiostream_plays").fetchone()[0]
    assert after == before
    assert [x["track_id"] for x in d["recent"]][:1] == ["t_x"]
