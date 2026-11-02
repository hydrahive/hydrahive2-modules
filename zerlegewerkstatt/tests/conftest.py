"""Isolierte Fixtures der Zerlege-Werkstatt."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402,F401
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

import bcrypt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MOD_PREFIX = "/api/modules/zerlegewerkstatt"
PROJECT_ID = "test-project-zerlege"
OTHER_PROJECT_ID = "other-project-zerlege"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        root = Path(tmpdir)
        os.environ.update({
            "HH_SECRET_KEY": "test-secret-key-for-jwt-signing",
            "HH_DISCORD_ENABLED": "0", "HH_WA_ENABLED": "0",
            "HH_AGENTLINK_URL": "", "HH_PG_MIRROR_DSN": "",
        })
        (root / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)
        password = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (root / "config" / "users.json").write_text(json.dumps({
            "alice": {"password_hash": password, "role": "user"},
            "bob": {"password_hash": password, "role": "user"},
        }))
        for pid, member in ((PROJECT_ID, "alice"), (OTHER_PROJECT_ID, "bob")):
            pdir = root / "data" / "projects" / pid
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "config.json").write_text(json.dumps({
                "id": pid, "name": pid, "members": [member], "created_by": member,
            }))

        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()
        apply_module_migrations("zerlegewerkstatt", MODULE_DIR / "migrations")
        from hydrahive.api import main
        from backend.routes import router
        main.app.include_router(router, prefix=MOD_PREFIX)
        yield root


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from hydrahive.api import main
    from hydrahive.db import init_db
    init_db()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from hydrahive.settings import settings
        settings.ensure_dirs()
        yield

    old = main.app.router.lifespan_context
    main.app.router.lifespan_context = lifespan
    with TestClient(main.app) as instance:
        yield instance
    main.app.router.lifespan_context = old


def _login(client, user: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return _login(client, "alice")


@pytest.fixture
def bob(client):
    return _login(client, "bob")


@pytest.fixture(autouse=True)
def clean_rows():
    with (
        only_own_rows("module_zerlege_jobs"),
        only_own_rows("module_zerlege_artifacts"),
        only_own_rows("module_zerlege_cases"),
    ):
        yield
