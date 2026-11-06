"""Isolated Game Studio module test fixtures."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
from _hh_isolation import (  # noqa: F401
    isolated_root,
    only_own_files,
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
    remove_test_tree,
)
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MOD_PREFIX = "/api/modules/game-studio"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        root = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (root / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt

        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (root / "config" / "users.json").write_text(
            json.dumps(
                {
                    "admin": {"password_hash": password_hash, "role": "admin"},
                    "testuser": {"password_hash": password_hash, "role": "user"},
                    "other": {"password_hash": password_hash, "role": "user"},
                }
            )
        )

        from backend.routes import router
        from hydrahive.api import main

        main.app.include_router(router, prefix=MOD_PREFIX)
        yield root


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from hydrahive.db import init_db

    init_db()

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    from hydrahive.api import main

    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.router.lifespan_context = original


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _module_state(setup_test_env, monkeypatch):
    from backend import overview, projects
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    from hydrahive.projects import config as project_config

    init_db()
    apply_module_migrations("game-studio", MODULE_DIR / "migrations")
    created: list[str] = []
    original_create = projects.create

    def tracked_create(*args, **kwargs):
        result = original_create(*args, **kwargs)
        created.append(result["project_id"])
        return result

    monkeypatch.setattr(projects, "create", tracked_create)
    monkeypatch.setattr(projects, "default_model", lambda: "test/model")
    monkeypatch.setattr(projects, "enable_share", lambda project_id, name: (True, ""))
    monkeypatch.setattr(projects, "is_share_enabled", lambda project_id: True)
    monkeypatch.setattr(projects.samba_manager, "share_user", lambda: "test-share")
    monkeypatch.setattr(overview, "samba_status", lambda: {
        "installed": True, "running": True, "user": "test-share", "platform": "linux"
    })
    yield
    for project_id in created:
        project_config.delete(project_id)
