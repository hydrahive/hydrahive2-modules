"""Test-Fixtures für Vibe (Muster hydralabor/tests/conftest.py).

incus wird nie echt aufgerufen: `fake_incus` ersetzt `backend.incus.run` (einziger Weg nach incus).
Die Isolation (`_hh_isolation`) ist in allen Modulen byte-gleich und wird zuerst importiert.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
from _hh_isolation import (  # noqa: F401 - pytest-Hooks, über conftest registriert
    isolated_root,
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
)

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

TABLES = ("module_vibe_projects", "module_vibe_versions")


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)
        import bcrypt
        ph = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "testuser": {"password_hash": ph, "role": "user"},
            "boss": {"password_hash": ph, "role": "admin"},
        }, indent=2))
        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("vibe", MODULE_DIR / "migrations")
        _declare_capabilities()
        _mount_like_core()
        yield tmp_path


def _mount_like_core() -> None:
    """Router über den echten Kern-Weg einhängen (Muster hydralabor/tests/conftest.py)."""
    from hydrahive.api import main
    from hydrahive.modules.context import ModuleContext
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY, LoadedModule

    import backend

    ctx = ModuleContext("vibe")
    backend.register(ctx)
    saved = dict(REGISTRY)
    REGISTRY.clear()
    REGISTRY["vibe"] = LoadedModule(name="vibe", manifest=ModuleManifest.load(MODULE_DIR / "manifest.json"),
                                    path=MODULE_DIR, ctx=ctx, loaded=True)
    try:
        main.mount_module_routers(main.app)
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)


def _declare_capabilities() -> None:
    from hydrahive.access.capabilities import catalog
    from hydrahive.modules.manifest import ModuleManifest
    catalog().register_module(ModuleManifest.load(MODULE_DIR / "manifest.json"))


@pytest.fixture
def db_ready(setup_test_env):
    with only_own_rows(*TABLES):
        yield


@pytest.fixture
def fake_incus(monkeypatch):
    from fake_incus import FakeIncus

    from backend import incus
    fake = FakeIncus()
    monkeypatch.setattr(incus, "run", fake.run)
    monkeypatch.setattr(incus, "run_to_file", fake.run_to_file)
    monkeypatch.setattr(incus, "available", lambda: True)
    return fake


@pytest.fixture
def client(setup_test_env, db_ready):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from hydrahive.api import main

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = original


def _login(client, name: str) -> dict:
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_headers(client):
    return _login(client, "testuser")


@pytest.fixture
def admin_headers(client):
    return _login(client, "boss")


@pytest.fixture(autouse=True)
def core_project_exists(monkeypatch, request):
    """Die Workspace-Tests arbeiten mit festen IDs (p1, p2) ohne echtes Kern-Projekt. `workspace.ensure()` verlangt
    unter der Sperre ein vorhandenes Kern-Projekt (Review 4: kein Neuanlegen nach dem Löschen) – hier gilt es für p1/p2
    als vorhanden. Tests, die das Gegenteil prüfen, verwenden echte Projekte und sind davon nicht betroffen."""
    from hydrahive.projects import config as project_config

    real_get = project_config.get

    def get(project_id):
        found = real_get(project_id)
        if found is None and project_id in ("p1", "p2"):
            return {"id": project_id}
        return found

    monkeypatch.setattr(project_config, "get", get)
