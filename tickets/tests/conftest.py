"""Isolierte Fixtures für das native Tickets-Modul."""
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
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MODULE_DIR = Path(__file__).resolve().parents[1]
CORE_SRC = MODULE_DIR.parents[1] / "hydrahive2" / "core" / "src"
for path in (MODULE_DIR, CORE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with isolated_root() as tmpdir:
        root = Path(tmpdir)
        os.environ.update(
            {
                "HH_SECRET_KEY": "tickets-test-secret-key",
                "HH_DISCORD_ENABLED": "0",
                "HH_WA_ENABLED": "0",
                "HH_AGENTLINK_URL": "",
                "HH_PG_MIRROR_DSN": "",
            }
        )
        (root / "data" / "agents").mkdir(parents=True, exist_ok=True)
        (root / "config").mkdir(parents=True, exist_ok=True)
        import bcrypt

        password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
        (root / "config" / "users.json").write_text(
            json.dumps(
                {
                    "admin": {"user_id": "user-admin", "password_hash": password_hash, "role": "admin"},
                    "member": {"user_id": "user-member", "password_hash": password_hash, "role": "user"},
                    "other": {"user_id": "user-other", "password_hash": password_hash, "role": "user"},
                }
            ),
            encoding="utf-8",
        )
        yield root


@pytest.fixture
def ticket_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("tickets", MODULE_DIR / "migrations")
    # Nach jedem Test nur die Zeilen entfernen, die er angelegt hat.
    # Kein Zurücksetzen von sqlite_sequence: sonst würden Ticketnummern wiederverwendet.
    with only_own_rows(
        "module_ticket_github_links",
        "module_ticket_github_connections",
        "module_ticket_notifications",
        "module_ticket_attachments",
        "module_ticket_events",
        "module_ticket_comments",
        "module_ticket_team_members",
        "module_ticket_teams",
        "module_tickets",
    ):
        yield setup_test_env


@pytest.fixture
def client(ticket_db):
    from backend.routes import router

    app = FastAPI()
    app.include_router(router, prefix="/api/modules/tickets")
    return TestClient(app)
