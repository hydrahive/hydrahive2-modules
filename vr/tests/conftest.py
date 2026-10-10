"""Self-contained Test-Fixtures fürs VR-Modul (isoliert über _hh_isolation)."""
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

MOD_PREFIX = "/api/modules/vr"
DEV_PREFIX = "/api/module-device/vr"
TABLES = ("module_vr_pairing", "module_vr_headsets")


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
            "alice": {"password_hash": ph, "role": "user"},
            "bob": {"password_hash": ph, "role": "user"},
        }, indent=2))

        from hydrahive.api import main
        from backend.pair_routes import device_auth, device_router
        from backend.pair_routes import router as pair_router
        from backend.routes import router
        main.app.include_router(router, prefix=MOD_PREFIX)
        main.app.include_router(pair_router, prefix=MOD_PREFIX)
        _mount_device(main.app, device_router, device_auth)
        yield tmp_path


def _mount_device(app, router, auth) -> None:
    """Wie der Kern (api/module_devices.py): Rate-Limit + auth als Pflicht-Dependencies."""
    from fastapi import Depends
    try:
        from hydrahive.api.module_devices import DEVICE_PREFIX, _rate_limit_for
        deps = [Depends(_rate_limit_for("vr")), Depends(auth)]
        prefix = f"{DEVICE_PREFIX}/vr"
    except ImportError:
        deps, prefix = [Depends(auth)], DEV_PREFIX
    app.include_router(router, prefix=prefix, dependencies=deps)


@pytest.fixture(autouse=True)
def _vr_db(setup_test_env):
    """Migrierte Tabellen; nach jedem Test nur die eigenen Zeilen weg."""
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    init_db()
    apply_module_migrations("vr", MODULE_DIR / "migrations")
    with only_own_rows(*TABLES):
        yield


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    try:
        from hydrahive.api.middleware import inbound_ratelimit
        inbound_ratelimit.reset()
    except ImportError:
        pass
    yield


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
def login(client):
    def _login(name: str) -> dict:
        r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _login


@pytest.fixture(autouse=True)
def fresh_hub():
    """Jeder Test startet mit leerem Verteiler."""
    from backend import state
    from backend.hub import hub
    hub._subs.clear()
    state.clear()
    yield
    hub._subs.clear()
    state.clear()
