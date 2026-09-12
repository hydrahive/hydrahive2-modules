"""Self-contained Test-Fixtures fürs Musicplayer-Modul."""
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

MOD_PREFIX = "/api/modules/musicplayer"
PROJECT_A = "019efake-project-a"
PROJECT_B = "019efake-project-b"


def _project(project_id: str) -> dict:
    return {
        "id": project_id,
        "name": project_id,
        "created_by": "projectadmin",
        "members": [
            {"username": "reader", "role": "read"},
            {"username": "writer", "role": "write"},
        ],
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_DATA_DIR"] = str(tmp_path / "data")
        os.environ["HH_CONFIG_DIR"] = str(tmp_path / "config")
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing-at-least-32-bytes"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        users = {
            username: {"password_hash": password_hash, "role": role}
            for username, role in {
                "admin": "admin",
                "reader": "user",
                "writer": "user",
                "projectadmin": "user",
                "outsider": "user",
            }.items()
        }
        (tmp_path / "config" / "users.json").write_text(json.dumps(users, indent=2))

        for project_id in (PROJECT_A, PROJECT_B):
            project_dir = tmp_path / "data" / "projects" / project_id
            project_dir.mkdir(parents=True)
            (project_dir / "config.json").write_text(json.dumps(_project(project_id)))
            (tmp_path / "data" / "workspaces" / "projects" / project_id).mkdir(parents=True)

        from hydrahive.api import main
        from backend.import_routes import router as import_router
        from backend.routes import router
        main.app.include_router(router, prefix=MOD_PREFIX)
        main.app.include_router(import_router, prefix=MOD_PREFIX)
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
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.router.lifespan_context = original


def _headers(client, username: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "testpass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    return _headers(client, "admin")


@pytest.fixture
def reader_headers(client):
    return _headers(client, "reader")


@pytest.fixture
def writer_headers(client):
    return _headers(client, "writer")


@pytest.fixture
def project_admin_headers(client):
    return _headers(client, "projectadmin")


@pytest.fixture
def outsider_headers(client):
    return _headers(client, "outsider")


@pytest.fixture
def reader_token(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "reader", "password": "testpass123"},
    )
    return response.json()["access_token"]


@pytest.fixture(autouse=True)
def _tracks_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations
    from backend import storage

    init_db()
    apply_module_migrations("musicplayer", MODULE_DIR / "migrations")
    with db() as connection:
        connection.execute("DELETE FROM module_musicplayer_tracks")

    for project_id in (PROJECT_A, PROJECT_B):
        audio_dir = storage.audio_dir(project_id)
        for file in audio_dir.glob("*.mp3"):
            file.unlink(missing_ok=True)
        generated_dir = storage.project_workspace(project_id) / "generated"
        if generated_dir.exists():
            for file in generated_dir.glob("*.mp3"):
                file.unlink(missing_ok=True)

    legacy_dir = storage.legacy_storage_dir()
    if legacy_dir.exists():
        for file in legacy_dir.glob("*.mp3"):
            file.unlink(missing_ok=True)
    yield
