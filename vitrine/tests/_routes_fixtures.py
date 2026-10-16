"""Gemeinsame Fixtures der Routen-Tests: echter Kern-Weg mit Modul-Tor module.vitrine, isoliertes Datenverzeichnis."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from _hh_isolation import isolated_root, only_own_files

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
    (d / "inbox").mkdir(parents=True, exist_ok=True)
    with only_own_files(d / "videos"), only_own_files(d, "*.json"), only_own_files(d, "*.jpg"), \
            only_own_files(d / "inbox"):
        yield d


@pytest.fixture(autouse=True)
def _ffprobe(monkeypatch):
    from backend import videos
    monkeypatch.setattr(videos, "probe", lambda p: {"ok": b"VIDEO" in p.read_bytes()[:16], "duration": 10.0, "width": 720, "height": 1280})
