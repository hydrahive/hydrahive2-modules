"""Backend-Routen über den echten Kern-Weg (Modul-Tor module.vitrine). Braucht den Kern; ohne → übersprungen."""
# ruff: noqa: F811 - pytest-Fixtures aus _routes_fixtures werden als gleichnamige Parameter genutzt
from __future__ import annotations

import io
import json

import pytest

pytest.importorskip("hydrahive")
from _routes_fixtures import B, _ffprobe, _h, admin, client, data, env  # noqa: E402, F401 - pytest-Fixtures


def test_nur_admin(client, admin):
    assert client.get(f"{B}/config").status_code == 401
    assert client.get(f"{B}/config", headers=_h(client, "nutzer")).status_code == 403
    assert client.get(f"{B}/config", headers=admin).status_code == 200


def test_config_lesen_und_schreiben(client, admin, data):
    (data / "videos" / "herbst.mp4").write_bytes(b"VIDEO")
    c = client.get(f"{B}/config", headers=admin).json()
    c["rules"] = [{"id": "a", "name": "Herbst", "kind": "season", "season": "autumn", "priority": 10,
                   "enabled": True, "videos": ["herbst.mp4"]}]
    c["night"] = {"enabled": True, "from": "23:00", "to": "07:00", "mode": "off"}
    c["fps"], c["message_seconds"] = 12, 45
    r = client.put(f"{B}/config", json=c, headers=admin)
    assert r.status_code == 200, r.text
    saved = json.loads((data / "config.json").read_text())
    assert saved["night"]["mode"] == "off" and saved["fps"] == 12 and saved["message_seconds"] == 45


def test_config_standardwerte_fuer_neue_felder(client, admin, data):
    c = client.get(f"{B}/config", headers=admin).json()
    assert c["fps"] == 24 and c["message_seconds"] == 15
    c.pop("fps")
    c.pop("message_seconds")                       # altes Cockpit ohne die Felder
    assert client.put(f"{B}/config", json=c, headers=admin).status_code == 200
    saved = json.loads((data / "config.json").read_text())
    assert saved["fps"] == 24 and saved["message_seconds"] == 15


@pytest.mark.parametrize("bad", [
    {"rules": [{"id": "a", "name": "X", "kind": "mond", "priority": 1, "enabled": True, "videos": []}]},
    {"rules": [{"id": "a", "name": "X", "kind": "range", "from": "13-40", "to": "01-01", "priority": 1, "enabled": True, "videos": []}]},
    {"rules": [{"id": "a", "name": "X", "kind": "season", "season": "autumn", "priority": 1, "enabled": True, "videos": ["../../etc/passwd"]}]},
    {"night": {"enabled": True, "from": "99:00", "to": "07:00", "mode": "dim"}},
    {"night": {"enabled": True, "from": "23:00", "to": "07:00", "mode": "disco"}},
    {"rotate_minutes": -1},
    {"fps": 11}, {"fps": 31}, {"fps": "schnell"},
    {"message_seconds": 4}, {"message_seconds": 121},
])
def test_config_ungueltig_422(client, admin, data, bad):
    base = client.get(f"{B}/config", headers=admin).json()
    r = client.put(f"{B}/config", json={**base, **bad}, headers=admin)
    assert r.status_code == 422, r.text
    assert not (data / "config.json").exists()


def test_video_hochladen_liste_loeschen(client, admin, data):
    r = client.post(f"{B}/videos", headers=admin, files={"file": ("Mein Herbst!.mp4", io.BytesIO(b"VIDEO-daten"), "video/mp4")})
    assert r.status_code == 201, r.text
    name = r.json()["name"]
    assert name == "mein-herbst.mp4" and (data / "videos" / name).exists()
    lst = client.get(f"{B}/videos", headers=admin).json()
    assert [v["name"] for v in lst] == [name] and lst[0]["size"] == len(b"VIDEO-daten")
    r2 = client.post(f"{B}/videos", headers=admin, files={"file": ("mein herbst.mp4", io.BytesIO(b"VIDEO-2"), "video/mp4")})
    assert r2.json()["name"] == "mein-herbst-2.mp4", "kein Überschreiben"
    assert client.delete(f"{B}/videos/{name}", headers=admin).status_code == 204
    assert not (data / "videos" / name).exists()


@pytest.mark.parametrize(("fname", "inhalt"), [("bild.jpg", b"VIDEO"), ("skript.sh", b"VIDEO"), ("kein.mp4", b"MUELL")])
def test_upload_abgelehnt(client, admin, data, fname, inhalt):
    r = client.post(f"{B}/videos", headers=admin, files={"file": (fname, io.BytesIO(inhalt), "application/octet-stream")})
    assert r.status_code == 400
    assert list((data / "videos").iterdir()) == []


def test_upload_zu_gross(client, admin, data, monkeypatch):
    from backend import videos
    monkeypatch.setattr(videos, "MAX_BYTES", 10)
    r = client.post(f"{B}/videos", headers=admin, files={"file": ("a.mp4", io.BytesIO(b"VIDEO" * 5), "video/mp4")})
    assert r.status_code == 413 and list((data / "videos").iterdir()) == []


@pytest.mark.parametrize("name", ["..%2Fconfig.json", "%2Fetc%2Fpasswd", ".versteckt.mp4", "gibtsnicht.mp4"])
def test_loeschen_nur_eigene_dateien(client, admin, data, name):
    (data / "config.json").write_text("{}")
    assert client.delete(f"{B}/videos/{name}", headers=admin).status_code in (400, 404)
    assert (data / "config.json").exists()


def test_vorlagen_und_simulation(client, admin, data):
    (data / "videos" / "weihnachten.mp4").write_bytes(b"VIDEO")
    (data / "videos" / "herbst.mp4").write_bytes(b"VIDEO")
    tpl = client.get(f"{B}/templates", headers=admin).json()
    weih = next(t for t in tpl if t["name"] == "Weihnachten")
    c = client.get(f"{B}/config", headers=admin).json()
    c["rules"] = [{**weih, "id": "w", "enabled": True, "videos": ["weihnachten.mp4"]},
                  {"id": "h", "name": "Herbst", "kind": "season", "season": "autumn", "priority": 10, "enabled": True, "videos": ["herbst.mp4"]}]
    assert client.put(f"{B}/config", json=c, headers=admin).status_code == 200
    s = client.post(f"{B}/simulate", json={"at": "2026-12-24T19:00"}, headers=admin).json()
    assert s == {"video": "weihnachten.mp4", "rule": "Weihnachten", "holiday": "Weihnachten", "night": None}
    assert client.post(f"{B}/simulate", json={"at": "2026-10-15T12:00"}, headers=admin).json()["video"] == "herbst.mp4"
    assert client.post(f"{B}/simulate", json={"at": "kein-datum"}, headers=admin).status_code == 422


def test_vorschau(client, admin, data):
    assert client.get(f"{B}/preview.jpg", headers=admin).status_code == 404
    (data / "preview.jpg").write_bytes(b"\xff\xd8jpeg")
    r = client.get(f"{B}/preview.jpg", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.headers["cache-control"] == "no-store"
