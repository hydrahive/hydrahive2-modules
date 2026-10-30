"""Test-Fixtures für Hydra-Labor (Muster radiostream/tests/conftest.py).

incus wird nie echt aufgerufen: `fake_incus` ersetzt `backend.incus.run` (einziger Weg nach incus) und spielt ein
kleines incus mit Netzen, ACLs, Containern und Schnappschüssen nach.
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
    only_own_rows,
    pytest_collection_finish,
    pytest_configure,
    pytest_runtest_call,
    pytest_runtest_setup,
    pytest_unconfigure,
)

MODULE_DIR = Path(__file__).resolve().parents[1]
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

TABLES = ("module_hydralabor_state",)


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
        from hydrahive.db import init_db
        from hydrahive.modules.migrations import apply_module_migrations
        init_db()                               # Projekte löschen braucht die Kern-Tabellen (smb_mounts …)
        apply_module_migrations("hydralabor", MODULE_DIR / "migrations")
        yield tmp_path


@pytest.fixture
def db_ready(setup_test_env):
    with only_own_rows(*TABLES):
        yield


@pytest.fixture
def fake_incus(monkeypatch):
    from backend import incus
    from fake_incus import FakeIncus
    fake = FakeIncus()
    monkeypatch.setattr(incus, "run", fake.run)
    monkeypatch.setattr(incus, "available", lambda: True)
    return fake
