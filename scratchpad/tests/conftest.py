"""Eigenständige Test-Fixtures für das Ideen-Modul (scratchpad).

Hängt den Modul-Router wie der Kern unter /api/modules/scratchpad an die App.
Nutzer: alice und bob (normal), root (System-Admin). Projekte: PROJECT_A gehört
alice, PROJECT_B gehört bob.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
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

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from helpers import MOD_PREFIX, PROJECT_A, PROJECT_B, TABLES  # noqa: E402


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
        pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "alice": {"password_hash": pw_hash, "role": "user"},
            "bob": {"password_hash": pw_hash, "role": "user"},
            "root": {"password_hash": pw_hash, "role": "admin"},
        }, indent=2))

        for pid, creator in ((PROJECT_A, "alice"), (PROJECT_B, "bob")):
            pdir = tmp_path / "data" / "projects" / pid
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "config.json").write_text(json.dumps({
                "id": pid, "name": f"Projekt {creator}", "members": [creator], "created_by": creator,
            }, indent=2))

        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("scratchpad", MODULE_DIR / "migrations")

        from hydrahive.api import main
        from backend.routes import router
        main.app.include_router(router, prefix=MOD_PREFIX)
        yield tmp_path


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    from hydrahive.api import main
    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = original


def _login(client, username: str) -> dict:
    r = client.post("/api/auth/login", json={"username": username, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return _login(client, "alice")


@pytest.fixture
def bob(client):
    return _login(client, "bob")


@pytest.fixture
def root(client):
    return _login(client, "root")


@pytest.fixture(autouse=True)
def clean_ideas(setup_test_env):
    with only_own_rows(*TABLES):
        yield
