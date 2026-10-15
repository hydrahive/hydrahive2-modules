"""Backend-Routen über den echten Kern-Weg (Modul-Tor module.vitrine). Braucht den Kern; ohne → übersprungen."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("hydrahive")
from fastapi.testclient import TestClient  # noqa: E402

from _hh_isolation import isolated_root  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
B = "/api/modules/vitrine"


@pytest.fixture(scope="module")
def env():
    with isolated_root() as tmp:
        root = Path(tmp)
        os.environ.update(HH_SECRET_KEY="test-secret-key-for-jwt-signing-at-least-32-bytes", HH_DISCORD_ENABLED="0",
                          HH_WA_ENABLED="0", HH_AGENTLINK_URL="", HH_PG_MIRROR_DSN="")
        (root / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)
        import bcrypt
        pw = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()
        (root / "config" / "users.json").write_text(json.dumps(
            {"admin": {"password_hash": pw, "role": "admin"}, "nutzer": {"password_hash": pw, "role": "user"}}))
        import backend
        from hydrahive.api import main
        from hydrahive.modules.context import ModuleContext
        from hydrahive.modules.manifest import ModuleManifest
        from hydrahive.modules.registry import REGISTRY, LoadedModule
        from hydrahive.access.capabilities import catalog
        manifest = ModuleManifest.load(MODULE_DIR / "manifest.json")
        catalog().register_module(manifest)          # wie lifespan.register_module_capabilities beim echten Start
        ctx = ModuleContext("vitrine")
        backend.register(ctx)
        saved = dict(REGISTRY)
        REGISTRY.clear()
        REGISTRY["vitrine"] = LoadedModule(name="vitrine", manifest=manifest,
                                           path=MODULE_DIR, ctx=ctx, loaded=True)
        try:
            main.mount_module_routers(main.app)
        finally:
            REGISTRY.clear()
            REGISTRY.update(saved)
        yield root
        catalog().unregister_module("vitrine")


@pytest.fixture
def client(env):
    from contextlib import asynccontextmanager

    from hydrahive.api import main
    from hydrahive.db import init_db
    init_db()

    @asynccontextmanager
    async def life(app):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    orig = main.app.router.lifespan_context
    main.app.router.lifespan_context = life
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = orig


def _h(client, user):
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return _h(client, "admin")


@pytest.fixture
def data(env):
    from hydrahive.settings import settings
    d = settings.data_dir / "vitrine"
    (d / "videos").mkdir(parents=True, exist_ok=True)
    yield d
    for p in (d / "videos").iterdir():
        p.unlink()
    (d / "config.json").unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _ffprobe(monkeypatch):
    from backend import videos
    monkeypatch.setattr(videos, "probe", lambda p: {"ok": b"VIDEO" in p.read_bytes()[:16], "duration": 10.0, "width": 720, "height": 1280})


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
    r = client.put(f"{B}/config", json=c, headers=admin)
    assert r.status_code == 200, r.text
    assert json.loads((data / "config.json").read_text())["night"]["mode"] == "off"


@pytest.mark.parametrize("bad", [
    {"rules": [{"id": "a", "name": "X", "kind": "mond", "priority": 1, "enabled": True, "videos": []}]},
    {"rules": [{"id": "a", "name": "X", "kind": "range", "from": "13-40", "to": "01-01", "priority": 1, "enabled": True, "videos": []}]},
    {"rules": [{"id": "a", "name": "X", "kind": "season", "season": "autumn", "priority": 1, "enabled": True, "videos": ["../../etc/passwd"]}]},
    {"night": {"enabled": True, "from": "99:00", "to": "07:00", "mode": "dim"}},
    {"night": {"enabled": True, "from": "23:00", "to": "07:00", "mode": "disco"}},
    {"rotate_minutes": -1},
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
