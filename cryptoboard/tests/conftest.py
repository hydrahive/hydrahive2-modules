"""Self-contained Test-Fixtures fürs Cryptoboard-Modul.

Eigenständig (kein Core-conftest), läuft im Hub-Repo ohne den Core-Testbaum.
Hängt die Modul-Router exakt wie der Core (mount_module_routers) unter
/api/modules/cryptoboard an die App.
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

MOD_PREFIX = "/api/modules/cryptoboard"


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        tmp_path = Path(tmpdir)
        os.environ["HH_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
        os.environ["HH_DISCORD_ENABLED"] = "0"
        os.environ["HH_WA_ENABLED"] = "0"
        os.environ["HH_AGENTLINK_URL"] = ""
        os.environ["HH_PG_MIRROR_DSN"] = ""
        os.environ.pop("HH_COINGECKO_API_KEY", None)
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
        from backend.routes import router as market_router
        from backend.watchlist_routes import router as watchlist_router
        from backend.portfolio_routes import router as portfolio_router
        from backend.import_routes import router as import_router
        from backend.analysis_routes import router as analysis_router
        from backend.alerts_routes import router as alerts_router
        from backend.valuation_routes import router as valuation_router
        from backend.wallet_routes import router as wallet_router
        main.app.include_router(market_router, prefix=MOD_PREFIX)
        main.app.include_router(watchlist_router, prefix=MOD_PREFIX)
        main.app.include_router(portfolio_router, prefix=MOD_PREFIX)
        main.app.include_router(import_router, prefix=MOD_PREFIX)
        main.app.include_router(analysis_router, prefix=MOD_PREFIX)
        main.app.include_router(alerts_router, prefix=MOD_PREFIX)
        main.app.include_router(valuation_router, prefix=MOD_PREFIX)
        main.app.include_router(wallet_router, prefix=MOD_PREFIX)
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
def _clear_cache():
    from backend import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _watchlist_db(setup_test_env):
    """Migrierte + leere Watchlist-Tabelle vor jedem Test."""
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("cryptoboard", MODULE_DIR / "migrations")
    with only_own_rows(
        "module_cryptoboard_watchlist",
        "module_cryptoboard_transactions",
        "module_cryptoboard_alerts",
        "module_cryptoboard_alert_events",
        "module_cryptoboard_price_history",
        "module_cryptoboard_addresses",
    ):
        yield
