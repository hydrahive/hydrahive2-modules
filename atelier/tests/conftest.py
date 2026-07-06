"""Self-contained Test-Fixtures fürs Atelier-Modul (Audio-Teil).

Eigenständig (kein Core-conftest); hängt den Audio-Router unter
/api/modules/atelier an die App. Legt zusätzlich ein Test-Projekt an (Atelier
ist projekt-gebunden — anders als die anderen Module).
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

MOD_PREFIX = "/api/modules/atelier"
PROJECT_ID = "test-project-atelier"
OTHER_PROJECT_ID = "other-project-atelier"


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
        (tmp_path / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (tmp_path / "config").mkdir(parents=True, exist_ok=True)

        import bcrypt
        ph = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (tmp_path / "config" / "users.json").write_text(json.dumps({
            "testuser": {"password_hash": ph, "role": "user"},
            "other": {"password_hash": ph, "role": "user"},
        }, indent=2))

        # Test-Projekte anlegen (members = wer darauf zugreifen darf).
        for pid, member in ((PROJECT_ID, "testuser"), (OTHER_PROJECT_ID, "other")):
            pdir = tmp_path / "data" / "projects" / pid
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "config.json").write_text(json.dumps({
                "id": pid, "name": pid, "members": [member], "created_by": member,
            }, indent=2))

        from hydrahive.api import main
        from backend.audio_routes import router as audio_router
        from backend.routes import router as main_router
        main.app.include_router(audio_router, prefix=MOD_PREFIX)
        main.app.include_router(main_router, prefix=MOD_PREFIX)
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


@pytest.fixture
def other_headers(client):
    r = client.post("/api/auth/login", json={"username": "other", "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _clean_atelier_dirs(setup_test_env):
    """Leert die Atelier-Ordner beider Test-Projekte vor jedem Test (Dateisystem
    ist nicht wie eine DB automatisch isoliert — Tracks/Profile aus vorherigen
    Tests würden sonst in der Bibliothek anderer Tests auftauchen)."""
    import shutil
    from backend import storage
    for pid in (PROJECT_ID, OTHER_PROJECT_ID):
        root = storage.atelier_root(pid)
        if root.is_dir():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
    yield
