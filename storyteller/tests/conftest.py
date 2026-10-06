"""Self-contained Test-Fixtures fürs Storyteller-Modul.

Eigenständig (kein Core-conftest), hängt den Modul-Router wie der Core unter
/api/modules/storyteller an die App. Zwei Test-Projekte mit je einem Mitglied,
damit Zugriffsschutz zwischen Projekten geprüft werden kann.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hh_isolation import (  # noqa: E402, F401 - pytest-Hooks, über conftest registriert
    isolated_root,
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

MOD_PREFIX = "/api/modules/storyteller"
PROJECT_ID = "test-project-story"
OTHER_PROJECT_ID = "other-project-story"


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
            "other": {"password_hash": ph, "role": "user"},
        }, indent=2))

        for pid, member in ((PROJECT_ID, "testuser"), (OTHER_PROJECT_ID, "other")):
            pdir = tmp_path / "data" / "projects" / pid
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "config.json").write_text(json.dumps({
                "id": pid, "name": pid, "members": [member], "created_by": member,
            }, indent=2))

        from hydrahive.api import main
        from backend import router
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


def _login(client, user: str) -> dict:
    r = client.post("/api/auth/login", json={"username": user, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return _login(client, "testuser")


@pytest.fixture
def other_headers(client):
    return _login(client, "other")


@pytest.fixture(autouse=True)
def _clean_story_dirs(setup_test_env):
    """Storyteller-Ordner beider Test-Projekte vor jedem Test leeren (Dateisystem ist nicht isoliert)."""
    from backend import storage
    from backend.ai import _busy, _rate
    for pid in (PROJECT_ID, OTHER_PROJECT_ID):
        root = storage.story_root(pid)
        if root.is_dir():
            remove_test_tree(root)
    _rate.clear()
    _busy.clear()
    yield
