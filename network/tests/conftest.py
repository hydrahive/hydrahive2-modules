"""Test-Fixtures fürs Modul Netzwerk (Muster radiostream/tests/conftest.py).

Isolierter Datenordner, zwei Nutzer (Nutzer mit Modul-Freigabe, Admin), Router unter /api/modules/network.
Geräte werden nie echt angesprochen: Tests ersetzen den HTTP-Weg (unifi_client._get/_post, fritz_igd._soap,
probe._run) durch Antworten aus tests/fixtures (echte Antworten vom 01.11.2026, ohne Schlüssel und MAC-Adressen).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest
from _hh_isolation import (  # noqa: F401 - pytest-Hooks, über conftest registriert
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
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

MOD_PREFIX = "/api/modules/network"
TABLES = ("module_network_config", "module_network_samples", "module_network_events", "module_network_speedtests",
          "module_network_udm_series", "access_capability_grants", "access_audit")
SECRET = "geheimer-UDM-Schluessel-123"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


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
            "boss": {"password_hash": ph, "role": "admin"},
        }, indent=2))

        _declare_capabilities()
        _mount_like_core()
        yield tmp_path


def _mount_like_core() -> None:
    """Router über den echten Kern-Weg einhängen (Modul-Tor vor /api/modules), wie radiostream."""
    import backend
    from hydrahive.api import main
    from hydrahive.modules.context import ModuleContext
    from hydrahive.modules.manifest import ModuleManifest
    from hydrahive.modules.registry import REGISTRY, LoadedModule

    ctx = ModuleContext("network")
    backend.register(ctx)
    saved = dict(REGISTRY)
    REGISTRY.clear()
    REGISTRY["network"] = LoadedModule(name="network", manifest=ModuleManifest.load(MODULE_DIR / "manifest.json"),
                                           path=MODULE_DIR, ctx=ctx, loaded=True)
    try:
        main.mount_module_routers(main.app)
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)


def _declare_capabilities() -> None:
    """Freigaben aus dem Manifest bekannt machen (wie der Kern beim Laden), sonst gälte network.configure als offen."""
    from hydrahive.access.capabilities import catalog
    from hydrahive.modules.manifest import ModuleManifest
    catalog().register_module(ModuleManifest.load(MODULE_DIR / "manifest.json"))


def _migrate() -> None:
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    init_db()
    apply_module_migrations("network", MODULE_DIR / "migrations")


@pytest.fixture
def db_ready(setup_test_env):
    """Tabellen da; nach dem Test nur die im Test neu angelegten Zeilen weg (only_own_rows)."""
    _migrate()
    with only_own_rows(*TABLES):
        _grant_module_to_user()
        yield


def _grant_module_to_user() -> None:
    """Das Modul ist admin_only (Manifest). Ein Admin gibt es dem Test-Nutzer frei – network.configure bekommt er
    NICHT."""
    from hydrahive.access import grants
    from hydrahive.api.middleware.users import get_by_username
    uid = get_by_username("testuser")["user_id"]
    grants.grant("module.network", "user", uid, "use", actor_id="test")


@pytest.fixture
def client(setup_test_env, db_ready):
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


def _login(client, name: str) -> dict:
    r = client.post("/api/auth/login", json={"username": name, "password": "testpass123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def user_headers(client):
    return _login(client, "testuser")


@pytest.fixture
def admin_headers(client):
    return _login(client, "boss")


@pytest.fixture
def safe(setup_test_env):
    """Safe-Einträge des Admins: „udm“ (API-Schlüssel, Typ bearer wie bei Till) und „fritz“ (basic)."""
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import delete_credential, save_credential
    ok, msg = save_credential("boss", Credential(name="udm", type="bearer", value=SECRET,
                                                 url_pattern="https://192.168.178.1/"))
    assert ok, msg
    ok, msg = save_credential("boss", Credential(name="fritz", type="basic", value="hydra:fritz-Passwort-9",
                                                 url_pattern="http://192.168.3.1/"))
    assert ok, msg
    yield {"udm": "udm", "fritz": "fritz"}
    delete_credential("boss", "udm")
    delete_credential("boss", "fritz")


@pytest.fixture
def udm_data() -> dict:
    return json.loads((FIXTURES / "udm.json").read_text())
