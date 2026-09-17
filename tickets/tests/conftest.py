"""Isolierte Fixtures für das native Tickets-Modul."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parents[1]
CORE_SRC = MODULE_DIR.parents[1] / "hydrahive2" / "core" / "src"
for path in (MODULE_DIR, CORE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        os.environ.update(
            {
                "HH_DATA_DIR": str(root / "data"),
                "HH_CONFIG_DIR": str(root / "config"),
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
                    "admin": {"password_hash": password_hash, "role": "admin"},
                    "member": {"password_hash": password_hash, "role": "user"},
                }
            ),
            encoding="utf-8",
        )
        yield root


@pytest.fixture
def ticket_db(setup_test_env):
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("tickets", MODULE_DIR / "migrations")
    with db() as connection:
        for table in (
            "module_ticket_notifications",
            "module_ticket_attachments",
            "module_ticket_events",
            "module_ticket_comments",
            "module_ticket_team_members",
            "module_ticket_teams",
            "module_tickets",
        ):
            connection.execute(f"DELETE FROM {table}")
    return setup_test_env
