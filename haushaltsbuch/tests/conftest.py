from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

MODULE_DIR = Path(__file__).resolve().parents[1]
CORE_SRC = MODULE_DIR.parents[1] / "hydrahive2" / "core" / "src"
for path in (MODULE_DIR, CORE_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

_TMP = tempfile.TemporaryDirectory()
_ROOT = Path(_TMP.name)
os.environ.update(
    {
        "HH_DATA_DIR": str(_ROOT / "data"),
        "HH_CONFIG_DIR": str(_ROOT / "config"),
        "HH_SECRET_KEY": "haushaltsbuch-test-secret-key",
        "HH_DISCORD_ENABLED": "0",
        "HH_WA_ENABLED": "0",
        "HH_AGENTLINK_URL": "",
        "HH_PG_MIRROR_DSN": "",
    }
)
(_ROOT / "data" / "agents").mkdir(parents=True)
(_ROOT / "config").mkdir(parents=True)
_password = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("ascii")
(_ROOT / "config" / "users.json").write_text(
    json.dumps(
        {
            "owner": {
                "user_id": "user-owner",
                "password_hash": _password,
                "role": "user",
            },
            "member": {
                "user_id": "user-member",
                "password_hash": _password,
                "role": "user",
            },
            "outsider": {
                "user_id": "user-outsider",
                "password_hash": _password,
                "role": "user",
            },
        }
    )
)

PREFIX = "/api/modules/haushaltsbuch"


@pytest.fixture(scope="session")
def app() -> FastAPI:
    from backend import (
        household_router, import_router, ledger_router, loyalty_router,
        planning_router, router,
    )

    instance = FastAPI()
    for module_router in (
        router, household_router, import_router, ledger_router, loyalty_router,
        planning_router,
    ):
        instance.include_router(module_router, prefix=PREFIX)
    return instance


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    from hydrahive.db import init_db
    from hydrahive.db.connection import db
    from hydrahive.modules.migrations import apply_module_migrations

    init_db()
    apply_module_migrations("haushaltsbuch", MODULE_DIR / "migrations")
    with db() as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in reversed(
            (
                "households",
                "members",
                "loyalty_connections",
                "loyalty_partners",
                "loyalty_sync_runs",
                "loyalty_balances",
                "loyalty_activities",
                "loyalty_expirations",
                "loyalty_coupons",
                "invites",
                "accounts",
                "categories",
                "transactions",
                "postings",
                "budgets",
                "budget_periods",
                "budget_adjustments",
                "recurring_rules",
                "audit_events",
                "import_profiles",
                "import_batches",
                "import_rows",
            )
        ):
            conn.execute(f"DELETE FROM module_haushaltsbuch_{table}")
        conn.execute("PRAGMA foreign_keys=ON")
    return TestClient(app)


def headers(username: str) -> dict[str, str]:
    from hydrahive.api.middleware.auth import create_token

    users = {
        "owner": "user-owner",
        "member": "user-member",
        "outsider": "user-outsider",
    }
    return {
        "Authorization": f"Bearer {create_token(username, 'user', users[username])}"
    }


@pytest.fixture
def owner_headers() -> dict[str, str]:
    return headers("owner")


@pytest.fixture
def member_headers() -> dict[str, str]:
    return headers("member")


@pytest.fixture
def outsider_headers() -> dict[str, str]:
    return headers("outsider")
