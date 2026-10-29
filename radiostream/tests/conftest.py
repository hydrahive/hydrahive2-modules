"""Test-Fixtures fürs Modul Radiostream (Muster wie diagramme/tests/conftest.py).

Isolierter Datenordner, drei Nutzer (Nutzer, anderer Nutzer, Admin), Router unter /api/modules/radiostream.
SMB wird nie echt angesprochen: `fake_share` ersetzt den Zugriff durch einen Ordnerbaum im Speicher (smb_fake.py).
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

MOD_PREFIX = "/api/modules/radiostream"
TABLES = ("module_radiostream_sources", "module_radiostream_tracks", "module_radiostream_scan_errors",
          "module_radiostream_plays", "module_radiostream_station")
SECRET = "geheim-Passwort-123"


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

        from backend.routes import router
        from hydrahive.api import main
        main.app.include_router(router, prefix=MOD_PREFIX)
        yield tmp_path


def _migrate() -> None:
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations
    init_db()
    apply_module_migrations("radiostream", MODULE_DIR / "migrations")


@pytest.fixture
def db_ready(setup_test_env):
    """Tabellen da; nach dem Test nur die im Test neu angelegten Zeilen weg (only_own_rows)."""
    _migrate()
    from backend import scan_state
    scan_state.reset()
    with only_own_rows(*TABLES):
        yield
    scan_state.reset()


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
    """Safe-Eintrag „plexmusik“ (basic) für den Admin; nach dem Test wieder weg."""
    from hydrahive.credentials.models import Credential
    from hydrahive.credentials.store import delete_credential, save_credential
    ok, msg = save_credential("boss", Credential(name="plexmusik", type="basic", value=f"musik:{SECRET}",
                                                 url_pattern="smb://nas.test/Musik/"))
    assert ok, msg
    yield "plexmusik"
    delete_credential("boss", "plexmusik")


@pytest.fixture
def fake_share(monkeypatch):
    """Ordnerbaum im Speicher statt SMB (smb_fake.FakeShare); merkt sich Anmeldungen und gelesene Dateien."""
    from backend import smb_source
    from smb_fake import FakeShare
    share = FakeShare()
    monkeypatch.setattr(smb_source, "_connect", share.connect)
    return share
