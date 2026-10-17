"""Test-Fixtures fürs Studio-Modul (Muster wie tonstudio/tests/conftest.py).

Isolierter Datenordner, zwei Nutzer mit je einem Projekt, Router unter /api/modules/studio.
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

MOD_PREFIX = "/api/modules/studio"
PROJECT_ID = "test-project-studio"
OTHER_PROJECT_ID = "other-project-studio"


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


def _login(client, name: str) -> dict:
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return _login(client, "testuser")


@pytest.fixture
def other_headers(client):
    return _login(client, "other")


def _wait_for_jobs(timeout: float = 10.0) -> None:
    import threading
    import time
    end = time.time() + timeout
    for t in threading.enumerate():
        if t.name.startswith("studio-") and t.is_alive():
            t.join(max(0.0, end - time.time()))


@pytest.fixture(autouse=True)
def _clean_project_dirs(setup_test_env):
    """Räumt nach jedem Test nur auf, was der Test selbst angelegt hat, und nur unter TEST_ROOT.

    only_own_files löscht Dateien; die im Test neu entstandenen, danach leeren Ordner entfernen wir hier (sonst sähe der
    nächste Test z. B. einen leeren studio/-Ordner, obwohl er selbst nichts angelegt hat)."""
    from hydrahive.projects._paths import ensure_workspace
    roots = [ensure_workspace(pid) for pid in (PROJECT_ID, OTHER_PROJECT_ID)]
    before = {d for r in roots for d in r.rglob("*") if d.is_dir()}
    with only_own_files(roots[0], "**/*"), only_own_files(roots[1], "**/*"):
        yield
        _wait_for_jobs()                      # Auftrags-Threads zu Ende kommen lassen, bevor aufgeräumt wird
    for r in roots:
        for d in sorted((d for d in r.rglob("*") if d.is_dir() and not d.is_symlink()), key=lambda x: -len(x.parts)):
            if d not in before and not any(d.iterdir()) and d.resolve().is_relative_to(setup_test_env.resolve()):
                d.rmdir()


@pytest.fixture
def ws(setup_test_env):
    """Workspace des Test-Projekts."""
    from hydrahive.projects._paths import ensure_workspace
    return ensure_workspace(PROJECT_ID)
