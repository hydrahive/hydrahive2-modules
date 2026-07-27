from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1]
CORE_SRC = MODULE_DIR.parents[1] / "hydrahive2" / "core" / "src"
for path in (MODULE_DIR, CORE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="mediacenter-tests-"))
os.environ["HH_DATA_DIR"] = str(_TEST_ROOT / "data")
os.environ["HH_CONFIG_DIR"] = str(_TEST_ROOT / "config")
os.environ["HH_SECRET_KEY"] = "mediacenter-test-secret-key-at-least-32-bytes"
os.environ["HH_DISCORD_ENABLED"] = "0"
os.environ["HH_WA_ENABLED"] = "0"
os.environ["HH_AGENTLINK_URL"] = ""
# Mediacenter-Adressen bewusst leeren: sonst erben die Tests die Konfiguration
# des Servers (systemd-Drop-in) und schlagen je nach Maschine unterschiedlich
# fehl. Wer eine Adresse braucht, setzt sie im Test selbst.
for _key in (
    "HH_MEDIACENTER_SAB_ORIGIN",
    "HH_MEDIACENTER_RADARR_ORIGIN",
    "HH_MEDIACENTER_SONARR_ORIGIN",
    "HH_MEDIACENTER_INDEXER_ORIGIN",
    "HH_MEDIACENTER_INDEXER_FILE_HOST",
    "HH_MEDIACENTER_COVER_HOSTS",
):
    os.environ.pop(_key, None)
os.environ["HH_PG_MIRROR_DSN"] = ""


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    (_TEST_ROOT / "data" / "agents").mkdir(parents=True, exist_ok=True)
    (_TEST_ROOT / "config").mkdir(parents=True, exist_ok=True)
    import bcrypt

    password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
    (_TEST_ROOT / "config" / "users.json").write_text(
        json.dumps(
            {
                "alice": {"password_hash": password_hash, "role": "user"},
                "bob": {"password_hash": password_hash, "role": "user"},
            }
        )
    )

    from hydrahive.api import main
    from backend.routes_jobs import router as jobs_router
    from backend.routes_search import router as search_router

    main.app.include_router(search_router, prefix="/api/modules/mediacenter")
    main.app.include_router(jobs_router, prefix="/api/modules/mediacenter")
    yield _TEST_ROOT
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture
def client(setup_test_env):
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from hydrahive.api import main
    from hydrahive.db import init_db

    init_db()

    @asynccontextmanager
    async def minimal_lifespan(app: FastAPI):
        from hydrahive.settings import settings

        settings.ensure_dirs()
        yield

    original = main.app.router.lifespan_context
    main.app.router.lifespan_context = minimal_lifespan
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.router.lifespan_context = original


@pytest.fixture
def alice(client):
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "testpass123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def bob(client):
    response = client.post(
        "/api/auth/login", json={"username": "bob", "password": "testpass123"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(autouse=True)
def clean_in_memory_state():
    from hydrahive.api.middleware.inbound_ratelimit import reset
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    from backend.job_store import clear_all
    from backend.result_registry import RESULTS

    init_db()
    apply_module_migrations("mediacenter", MODULE_DIR / "migrations")
    clear_all()
    RESULTS.clear()
    reset()
    yield
