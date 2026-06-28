"""Self-contained Test-Fixtures fürs Home-Assistant-Modul.

Eigenständig (kein Core-conftest), läuft im Hub-Repo ohne den Core-Testbaum.
Hängt den Modul-Router exakt wie der Core (mount_module_routers) unter
/api/modules/homeassistant an die App. Kein echter HA-Traffic — der client wird
in den Tests gemockt.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MOD_PREFIX = "/api/modules/homeassistant"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_DATA_DIR"] = str(tmp_path / "data")
        os.environ["HH_CONFIG_DIR"] = str(tmp_path / "config")
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        os.environ.pop("HH_HOMEASSISTANT_URL", None)
        os.environ.pop("HH_HOMEASSISTANT_TOKEN", None)
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        ph = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "testuser": {"password_hash": ph, "role": "user"},
            "other": {"password_hash": ph, "role": "user"},
            "admin": {"password_hash": ph, "role": "admin"},
        }, indent=2))

        from hydrahive.api import main
        from backend.routes import router
        main.app.include_router(router, prefix=MOD_PREFIX)
        yield tmp_path


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
    with TestClient(main.app) as c:
        yield c
    main.app.router.lifespan_context = original


@pytest.fixture
def auth_headers(client):
    r = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _favorites_db(setup_test_env):
    """Migrierte + leere Favoriten-Tabelle vor jedem Test."""
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("homeassistant", MODULE_DIR / "migrations")
    with db() as c:
        c.execute("DELETE FROM module_homeassistant_favorites")
    yield
